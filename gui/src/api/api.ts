import { api } from './client.js'

export type JarvisStatus = {
  online: boolean
  listening: boolean
  speaking: boolean
  version?: string
}

export async function getStatus(): Promise<JarvisStatus> {
  const { data } = await api.get('/api/status')
  return data
}

export async function setStatus(patch: Partial<JarvisStatus>): Promise<JarvisStatus> {
  const { data } = await api.post('/api/status/toggle', patch)
    return data as JarvisStatus;
}

export type JarvisSettings = {
  stt_device?: string
  tts_voice?: string
  locale?: string
  openai_key?: string | null
}

export async function getSettings(): Promise<JarvisSettings> {
  const { data } = await api.get('/api/settings')
  return data
}

export async function updateSettings(patch: Partial<JarvisSettings>): Promise<JarvisSettings> {
  const { data } = await api.post('/api/settings', patch)
  return data
}

export function connectLogsWS(): WebSocket {
  // Expect FastAPI at ws://127.0.0.1:8000/api/logs/stream
  const ws = new WebSocket('ws://127.0.0.1:8000/api/logs/stream')
  return ws
}


export type IntentFile = {
  name: string;
};

export type IntentFileContent = {
  name: string;
  text: string;
};

/**
 * Допоміжна функція для коректного кодування шляху.
 * Вона кодує кожну частину шляху окремо, але залишає '/'
 * (напр., 'subdir/file with space.yml' -> 'subdir/file%20with%20space.yml')
 */
function encodePath(path: string): string {
  return path.split('/').map(encodeURIComponent).join('/');
}

/**
 * Отримати список усіх файлів інтентів.
 */
export async function listIntents(): Promise<IntentFile[]> {
  const { data } = await api.get<{ files: IntentFile[] }>('/api/intents');
  return data.files;
}

/**
 * Отримати вміст конкретного файлу інтенту.
 */
export async function getIntent(fname: string): Promise<IntentFileContent> {
  const encodedFname = encodePath(fname);
  const { data } = await api.get<IntentFileContent>(`/api/intents/${encodedFname}`);
  return data;
}

/**
 * Зберегти або оновити файл інтенту.
 * @param fname - Ім'я файлу (напр., "test.yml")
 * @param content - Текстовий вміст файлу (YAML)
 */
export async function saveIntent(fname: string, content: string): Promise<{ ok: boolean; name: string }> {
  const encodedFname = encodePath(fname);
  const { data } = await api.post(`/api/intents/${encodedFname}`, content, {
    headers: { 'Content-Type': 'text/plain' } // Надсилаємо як простий текст, оскільки бекенд очікує рядок
  });
  return data;
}

/**
 * Створити новий файл інтенту.
 * @param name - Бажане ім'я файлу (напр., "new_intent")
 */
export async function createIntent(name: string): Promise<{ ok: boolean; name: string }> {
  // Тут кодувати не треба, оскільки 'name' йде в тілі запиту (body)
  const { data } = await api.post('/api/intents/new', { name });
  return data;
}

/**
 * Видалити файл інтенту.
 */
export async function deleteIntent(fname: string): Promise<{ ok: boolean }> {
  const encodedFname = encodePath(fname);
  const { data } = await api.delete(`/api/intents/${encodedFname}`);
  return data;
}
