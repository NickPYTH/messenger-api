// signaling-server.js
const WebSocket = require('ws');
const wss = new WebSocket.Server({ port: 8080 });
const pendingOffers = new Map(); // roomId -> offer data

// Хранилище комнат и клиентов
const rooms = new Map(); // roomId -> { clients: Set, sender: WebSocket }
const clients = new Map(); // WebSocket -> { type: 'sender'|'receiver', roomId: string }

console.log('🚀 Сигнальный сервер запущен на ws://localhost:8080');

function handleRequestOffer(ws, data) {
    const { roomId } = data;
    const clientInfo = clients.get(ws);

    if (!clientInfo || clientInfo.roomId !== roomId) {
        ws.send(JSON.stringify({
            type: 'error',
            message: 'Вы не в этой комнате'
        }));
        return;
    }

    const room = rooms.get(roomId);
    if (!room) {
        ws.send(JSON.stringify({
            type: 'error',
            message: 'Комната не найдена'
        }));
        return;
    }

    console.log(`📨 Запрос оффера от клиента в комнате ${roomId}`);

    // Отправляем сохраненный оффер если есть
    const savedOffer = pendingOffers.get(roomId);
    if (savedOffer) {
        console.log(`📤 Отправляю сохраненный оффер по запросу`);
        ws.send(JSON.stringify({
            type: 'offer',
            sdp: savedOffer.sdp,
            from: savedOffer.from || 'sender',
            roomId: roomId,
            timestamp: savedOffer.timestamp
        }));
    } else {
        console.log(`ℹ️ Нет сохраненного оффера для комнаты ${roomId}`);

        // Запрашиваем оффер у отправителя
        if (room.sender && room.sender.readyState === WebSocket.OPEN) {
            room.sender.send(JSON.stringify({
                type: 'offer-requested',
                from: 'server',
                roomId: roomId,
                requester: clientInfo.username
            }));
        }

        ws.send(JSON.stringify({
            type: 'no-offer',
            message: 'Оффер еще не создан отправителем'
        }));
    }
}

wss.on('connection', (ws) => {
    console.log('🔌 Новый клиент подключен');

    ws.on('message', (message) => {
        try {
            const data = JSON.parse(message);
            console.log(`📨 ${data.type || 'unknown'} от ${data.from || 'unknown'}`);

            switch (data.type) {
                case 'join-room':
                    handleJoinRoom(ws, data);
                    break;

                case 'create-room':
                    handleCreateRoom(ws, data);
                    break;

                case 'list-rooms':
                    handleListRooms(ws);
                    break;

                case 'leave-room':
                    handleLeaveRoom(ws);
                    break;
                case 'request-offer':
                    handleRequestOffer(ws, data);
                    break;

                case 'broadcast-paused':
                    handleBroadcastPaused(ws, data);
                    break;

                case 'broadcast-resumed':
                    handleBroadcastResumed(ws, data);
                    break;

                case 'offer':
                case 'answer':
                case 'ice-candidate':
                    // Пересылаем сообщение всем в комнате кроме отправителя
                    forwardToRoom(ws, data);
                    break;

                default:
                    console.log('Неизвестный тип сообщения:', data.type);
            }
        } catch (error) {
            console.error('Ошибка обработки сообщения:', error);
        }
    });

    ws.on('close', () => {
        handleDisconnect(ws);
        console.log('🔌 Клиент отключен');
    });
});

function handleCreateRoom(ws, data) {
    const { roomName, roomId = generateRoomId() } = data;

    console.log(`🔄 Создание/возобновление комнаты ${roomId}`);

    // Проверяем, существует ли уже такая комната
    let room = rooms.get(roomId);

    if (room) {
        // Комната существует
        if (room.isActive) {
            // Комната уже активна - ошибка
            ws.send(JSON.stringify({
                type: 'error',
                message: 'Комната уже активна'
            }));
            return;
        } else {
            // Комната существует, но неактивна - возобновляем
            console.log(`▶️ Возобновление неактивной комнаты ${roomId}`);

            room.name = roomName || room.name || `Комната ${roomId}`;
            room.sender = ws;
            room.isActive = true;
            room.clients.add(ws);
            room.lastActive = new Date();

            // Очищаем старый оффер
            pendingOffers.delete(roomId);
        }
    } else {
        // Создаем новую комнату
        room = {
            name: roomName || `Комната ${roomId}`,
            clients: new Set([ws]),
            sender: ws,
            createdAt: new Date(),
            lastActive: new Date(),
            isActive: true
        };
        rooms.set(roomId, room);

        console.log(`✅ Создана новая комната "${roomName}" (${roomId})`);
    }

    clients.set(ws, {
        type: 'sender',
        roomId: roomId,
        username: data.username || 'Отправитель'
    });

    ws.send(JSON.stringify({
        type: 'room-created',
        roomId: roomId,
        roomName: room.name,
        isResumed: !!rooms.get(roomId)?.createdAt // Флаг возобновления
    }));

    // Уведомляем всех о новом списке комнат
    broadcastRoomList();
}

function handleJoinRoom(ws, data) {
    const { roomId } = data;
    const room = rooms.get(roomId);

    if (!room || !room.isActive) {
        ws.send(JSON.stringify({
            type: 'error',
            message: 'Комната не найдена или трансляция завершена'
        }));
        return;
    }

    // Добавляем клиента в комнату
    room.clients.add(ws);
    clients.set(ws, {
        type: 'receiver',
        roomId: roomId,
        username: data.username || 'Зритель'
    });

    console.log(`👤 Клиент присоединился к комнате ${roomId}`);
    console.log(`   Клиентов в комнате: ${room.clients.size}`);

    // Уведомляем отправителя о новом зрителе
    if (room.sender && room.sender.readyState === WebSocket.OPEN) {
        room.sender.send(JSON.stringify({
            type: 'viewer-joined',
            viewerId: ws._socket.remoteAddress,
            timestamp: new Date().toISOString()
        }));
    }

    // Отправляем информацию о комнате новому клиенту
    ws.send(JSON.stringify({
        type: 'room-joined',
        roomId: roomId,
        roomName: room.name,
        sender: clients.get(room.sender)?.username || 'Отправитель'
    }));

    // 🔥 КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ:
    // Если есть сохраненный оффер для этой комнаты - отправляем его новому клиенту
    const savedOffer = pendingOffers.get(roomId);
    if (savedOffer) {
        console.log(`📤 Отправляю сохраненный оффер новому клиенту в комнате ${roomId}`);

        // Даем клиенту время обработать room-joined
        setTimeout(() => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({
                    type: 'offer',
                    sdp: savedOffer.sdp,
                    from: savedOffer.from || 'sender',
                    roomId: roomId,
                    timestamp: savedOffer.timestamp
                }));
                console.log(`   ✅ Оффер отправлен новому клиенту`);
            }
        }, 500);
    } else {
        console.log(`ℹ️ Нет сохраненного оффера для комнаты ${roomId}`);
    }
}

function handleListRooms(ws) {
    const activeRooms = Array.from(rooms.entries())
        .filter(([id, room]) => room.isActive && room.sender) // Только активные
        .map(([id, room]) => ({
            id: id,
            name: room.name,
            viewers: room.clients.size - 1,
            createdAt: room.createdAt,
            lastActive: room.lastActive,
            sender: clients.get(room.sender)?.username || 'Неизвестно',
            status: room.isActive ? 'active' : 'paused'
        }));

    console.log(`📊 Отправляю список комнат: ${activeRooms.length} активных`);

    ws.send(JSON.stringify({
        type: 'room-list',
        rooms: activeRooms
    }));
}

function handleLeaveRoom(ws) {
    const clientInfo = clients.get(ws);
    if (!clientInfo) return;

    const room = rooms.get(clientInfo.roomId);
    if (!room) return;

    room.clients.delete(ws);
    clients.delete(ws);

    // Если отправитель ушел - закрываем комнату
    if (clientInfo.type === 'sender') {
        room.isActive = false;
        console.log(`🏁 Комната ${clientInfo.roomId} закрыта (отправитель ушел)`);

        // Удаляем сохраненный оффер
        pendingOffers.delete(clientInfo.roomId);

        // Уведомляем всех зрителей
        room.clients.forEach(client => {
            if (client.readyState === WebSocket.OPEN) {
                client.send(JSON.stringify({
                    type: 'broadcast-ended',
                    message: 'Трансляция завершена'
                }));
            }
        });

        rooms.delete(clientInfo.roomId);
    } else {
        console.log(`👋 Зритель покинул комнату ${clientInfo.roomId}`);
    }

    // Также очищайте старые офферы
    setInterval(() => {
        const now = Date.now();
        for (const [roomId, offer] of pendingOffers.entries()) {
            if (now - offer.timestamp > 5 * 60 * 1000) { // 5 минут
                pendingOffers.delete(roomId);
                console.log(`🗑️ Удален устаревший оффер для комнаты ${roomId}`);
            }
        }
    }, 60 * 1000);

    // Обновляем список комнат
    broadcastRoomList();
}

function handleDisconnect(ws) {
    handleLeaveRoom(ws);
}

function handleBroadcastPaused(ws, data) {
    const { roomId } = data;
    const room = rooms.get(roomId);

    if (!room) return;

    console.log(`⏸️ Трансляция в комнате ${roomId} приостановлена`);
    room.isActive = false;

    // Уведомляем всех зрителей
    room.clients.forEach(client => {
        if (client !== ws && client.readyState === WebSocket.OPEN) {
            client.send(JSON.stringify({
                type: 'broadcast-paused',
                roomId: roomId,
                message: data.message || 'Трансляция приостановлена'
            }));
        }
    });

    broadcastRoomList();
}

function handleBroadcastResumed(ws, data) {
    const { roomId } = data;
    const room = rooms.get(roomId);

    if (!room) return;

    console.log(`▶️ Трансляция в комнате ${roomId} возобновлена`);
    room.isActive = true;
    room.lastActive = new Date();

    // Уведомляем всех зрителей
    room.clients.forEach(client => {
        if (client !== ws && client.readyState === WebSocket.OPEN) {
            client.send(JSON.stringify({
                type: 'broadcast-resumed',
                roomId: roomId,
                message: data.message || 'Трансляция возобновлена'
            }));
        }
    });

    broadcastRoomList();
}

function forwardToRoom(senderWs, data) {
    const clientInfo = clients.get(senderWs);
    if (!clientInfo) {
        console.log(`❌ Клиент не найден в clients map`);
        return;
    }

    const room = rooms.get(clientInfo.roomId);
    if (!room) {
        console.log(`❌ Комната ${clientInfo.roomId} не найдена`);
        return;
    }

    console.log(`📨 [${data.type}] от ${clientInfo.type} в комнате ${clientInfo.roomId}`);
    console.log(`   Клиентов в комнате: ${room.clients.size}`);

    // Если это оффер - сохраняем
    if (data.type === 'offer') {
        console.log(`💾 Сохраняю оффер для комнаты ${clientInfo.roomId}`);
        pendingOffers.set(clientInfo.roomId, {
            sdp: data.sdp,
            from: data.from,
            timestamp: Date.now()
        });
    }

    // Отправляем всем кроме отправителя
    let sentCount = 0;
    const receiverClients = [];

    room.clients.forEach(client => {
        if (client !== senderWs) {
            receiverClients.push({
                client: client,
                type: clients.get(client)?.type || 'unknown',
                ready: client.readyState === WebSocket.OPEN
            });

            if (client.readyState === WebSocket.OPEN) {
                client.send(JSON.stringify(data));
                sentCount++;
            }
        }
    });

    console.log(`   ➡️ Отправлено ${sentCount}/${receiverClients.length} клиентам:`);
    receiverClients.forEach(rc => {
        console.log(`     - ${rc.type} (${rc.ready ? 'готов' : 'не готов'})`);
    });
}


function broadcastRoomList() {
    const activeRooms = Array.from(rooms.entries())
        .filter(([id, room]) => room.isActive && room.sender)
        .map(([id, room]) => ({
            id: id,
            name: room.name,
            viewers: room.clients.size - 1,
            sender: clients.get(room.sender)?.username || 'Неизвестно'
        }));

    // Рассылаем обновленный список всем подключенным клиентам
    wss.clients.forEach(client => {
        if (client.readyState === WebSocket.OPEN) {
            const clientInfo = clients.get(client);
            // Отправляем только если клиент не в активной комнате
            if (!clientInfo || clientInfo.type === 'receiver') {
                client.send(JSON.stringify({
                    type: 'room-list-update',
                    rooms: activeRooms
                }));
            }
        }
    });
}

function generateRoomId() {
    return Math.random().toString(36).substring(2, 8).toUpperCase();
}

// Очистка неактивных комнат каждые 5 минут
setInterval(() => {
    const now = Date.now();
    for (const [roomId, room] of rooms.entries()) {
        if (!room.isActive && now - room.createdAt > 30 * 60 * 1000) {
            rooms.delete(roomId);
            console.log(`🗑️ Удалена неактивная комната ${roomId}`);
        }
    }
}, 5 * 60 * 1000);