import os from "node:os";
export const app = {
  getPath: () => os.tmpdir(),
  isPackaged: false,
  getName: () => "meelu-test",
  getVersion: () => "0.0.0-test",
};
export const safeStorage = {
  isEncryptionAvailable: () => false,
  decryptString: () => "{}",
  encryptString: (s) => Buffer.from(s),
};
export const shell = {};
export const ipcMain = { handle() {}, on() {} };
export const BrowserWindow = class {};
export const session = { fromPartition: () => ({}) };
export const dialog = {};
export const net = {};
export default { app, safeStorage, shell, ipcMain, BrowserWindow, session, dialog, net };
