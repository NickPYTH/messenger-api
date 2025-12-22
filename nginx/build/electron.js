const { app, BrowserWindow, Tray, Menu, nativeImage } = require('electron');
const path = require('path');

// Важно объявить переменные глобально, чтобы сборщик мусора их не удалил
let tray = null;
let mainWindow = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 800,
    height: 600,
    // Если у вас frameless-окно, это не помешает работе
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false
    }
  });

  mainWindow.loadURL('https://sco1-vapp-09.sgp.ru/messenger'); // Загружайте свой React-интерфейс

  Menu.setApplicationMenu(null);

  // Перехватываем событие закрытия окна
  mainWindow.on('close', (event) => {
    // Если пользователь не выходит через Quit, просто прячем окно
    if (!app.isQuitting) {
      event.preventDefault();
      mainWindow.hide(); // Скрываем окно
      
      // Опционально: можно убрать иконку из панели задач (на Windows)
      // mainWindow.setSkipTaskbar(true);
      
      return false;
    }
  });
}

function createTray() {
  // Создаем иконку для трея. Лучше использовать абсолютный путь
  const iconPath = path.join(__dirname,'tray-icon.png'); // Укажите путь к вашей иконке

  let trayImage;
  console.log(__dirname)
  try {
    trayImage = nativeImage.createFromPath(iconPath);
  } catch (error) {
    // Если иконка не найдена, можно создать простую или использовать встроенную
    console.error('Tray icon not found, using default.');
    trayImage = nativeImage.createFromDataURL('data:image/png;base64,...'); // Простая заглушка
  }
  
  // Ресайзим иконку под нужный размер (обычно 16x16 или 32x32)
  trayImage = trayImage.resize({ width: 16, height: 16 });
  
  tray = new Tray(trayImage);
  tray.setToolTip('Корпоративный мессенджер'); // Текст при наведении

  // Создаем контекстное меню для иконки в трее
  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Открыть',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
          // mainWindow.setSkipTaskbar(false); // Возвращаем в панель задач, если убирали
        }
      }
    },
    { type: 'separator' }, // Разделительная линия
    {
      label: 'Выйти',
      click: () => {
        app.isQuitting = true;
        app.quit(); // Настоящий выход из приложения
      }
    }
  ]);

  tray.setContextMenu(contextMenu);
  
  // Дополнительно: показ окна по клику на иконку (опционально)
  tray.on('click', () => {
    if (mainWindow) {
      if (mainWindow.isVisible()) {
        mainWindow.hide();
      } else {
        mainWindow.show();
      }
    }
  });
}

// Инициализация приложения
app.whenReady().then(() => {
  createWindow();
  createTray();

  // Для macOS: если нет открытых окон, создать новое по активации приложения
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

// Важно: предотвращаем выход из приложения при закрытии всех окон
app.on('window-all-closed', (event) => {
  // На MacOS приложения обычно не закрываются, даже когда все окна закрыты
  if (process.platform !== 'darwin') {
    // Мы не вызываем app.quit(), поэтому приложение не закроется
    // Вместо этого окна уже скрыты в трей
    event.preventDefault();
  }
});