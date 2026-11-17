import { existsSync } from 'node:fs';
import { spawn, spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';

const root = fileURLToPath(new URL('../', import.meta.url));
const windows = process.platform === 'win32';
const python = process.env.PYTHON || resolve(root, '.venv', windows ? 'Scripts/python.exe' : 'bin/python');

function run(command, args) {
  const result = spawnSync(command, args, { cwd: root, stdio: 'inherit' });
  if (result.error || result.status !== 0) {
    console.error('Python setup failed. Install Python 3.13 or set PYTHON to a Python environment with requirements.lock installed.');
    process.exit(result.status || 1);
  }
}

if (!process.env.PYTHON && !existsSync(python)) {
  console.log('Creating .venv and installing Python dependencies (first run only)…');
  run(windows ? 'python' : 'python3', ['-m', 'venv', '.venv']);
  run(python, ['-m', 'pip', 'install', '-r', 'requirements.lock']);
}

const check = spawnSync(python, ['-c', 'import uvicorn; from app.config import Settings; Settings()'], {
  cwd: root,
  encoding: 'utf8',
});
if (check.error || check.status !== 0) {
  console.error('Cannot start: check .env against .env.example and install requirements.lock in your Python environment.');
  console.error('For the default environment: .venv/bin/python -m pip install -r requirements.lock (Windows: .venv\\Scripts\\python.exe).');
  process.exit(1);
}

// Read PORT from the same dotenv configuration used by the service, without printing secrets.
const portResult = spawnSync(python, ['-c', 'import os; from dotenv import load_dotenv; load_dotenv(); print(os.getenv("PORT", "8000"))'], {
  cwd: root,
  encoding: 'utf8',
});
const port = portResult.stdout?.trim();
if (portResult.status !== 0 || !/^\d+$/.test(port || '') || Number(port) < 1 || Number(port) > 65535) {
  console.error('PORT must be an integer between 1 and 65535.');
  process.exit(1);
}

console.log(`Starting Productivity AI at http://127.0.0.1:${port}`);
const child = spawn(python, ['-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', port, '--reload', '--no-access-log'], {
  cwd: root,
  stdio: 'inherit',
});
for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => child.kill(signal));
}
child.on('error', () => {
  console.error('Could not launch Python. Check your Python installation.');
  process.exitCode = 1;
});
child.on('exit', (code) => { process.exitCode = code ?? 0; });
