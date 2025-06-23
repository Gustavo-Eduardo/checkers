import { app, BrowserWindow } from "electron/main";

function createWindow() {
	const window = new BrowserWindow({
		width: 800,
		height: 800
	});
	window.loadFile("./index.html");
}

app.whenReady().then(() => {
	createWindow();
	app.on("activate", () => {
		if (BrowserWindow.getAllWindows().length === 0) {
			createWindow();
		}
	})
});

app.on("window-all-closed", () => {
	if (process.platform !== "darwin") {
		app.quit();
	}
})
