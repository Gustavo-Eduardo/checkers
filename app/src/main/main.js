const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

class CheckersApp {
  constructor() {
    this.mainWindow = null;
    this.pythonProcess = null;
  }

  async initialize() {
    await app.whenReady();
    this.startPythonBackend();
    this.createWindow();
    this.setupIPC();
    
    app.on('window-all-closed', () => {
      if (process.platform !== 'darwin') {
        this.cleanup();
        app.quit();
      }
    });

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) {
        this.createWindow();
      }
    });
  }

  startPythonBackend() {
    // Start Python backend process with Python 3.11 for MediaPipe support
    const pythonPath = process.platform === 'win32' ? 'python' : 
                      (process.env.HOME + '/.pyenv/shims/python3.11') || 'python3';
    const scriptPath = path.join(__dirname, '../../backend/main.py');
    
    console.log('Starting Python backend with Python 3.11:', scriptPath);
    
    // Set up environment for pyenv
    const env = { ...process.env };
    env.PATH = `${process.env.HOME}/.pyenv/bin:${env.PATH}`;
    env.PYENV_ROOT = `${process.env.HOME}/.pyenv`;
    
    this.pythonProcess = spawn(pythonPath, [scriptPath], {
      cwd: path.join(__dirname, '../../backend'),
      env: env
    });

    this.pythonProcess.stdout.on('data', (data) => {
      console.log(`Backend: ${data}`);
    });

    this.pythonProcess.stderr.on('data', (data) => {
      console.error(`Backend Error: ${data}`);
    });
    
    this.pythonProcess.on('error', (error) => {
      console.error('Failed to start Python backend:', error);
    });
    
    this.pythonProcess.on('exit', (code) => {
      console.log(`Python backend exited with code ${code}`);
      this.pythonProcess = null;
    });
  }

  createWindow() {
    this.mainWindow = new BrowserWindow({
      width: 1400,
      height: 900,
      minWidth: 1200,
      minHeight: 800,
      webPreferences: {
        preload: path.join(__dirname, '../preload/preload.js'),
        contextIsolation: true,
        nodeIntegration: false
      },
      backgroundColor: '#1a1a1a',
      titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
      title: 'Vision Checkers'
    });

    this.mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));
    
    // Open DevTools in development mode
    if (process.argv.includes('--dev')) {
      this.mainWindow.webContents.openDevTools();
    }
  }

  setupIPC() {
    ipcMain.handle('get-backend-status', async () => {
      return this.pythonProcess !== null && !this.pythonProcess.killed;
    });

    ipcMain.handle('restart-backend', async () => {
      if (this.pythonProcess) {
        this.pythonProcess.kill();
      }
      setTimeout(() => {
        this.startPythonBackend();
      }, 1000);
      return true;
    });
  }
  
  cleanup() {
    if (this.pythonProcess) {
      console.log('Stopping Python backend...');
      this.pythonProcess.kill();
    }
  }
}

const checkersApp = new CheckersApp();
checkersApp.initialize();