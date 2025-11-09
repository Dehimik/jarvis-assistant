import Header from '@/components/Header'
import Card from '@/components/Card'
import { useEffect, useState } from 'react'
import {
  listIntents,
  getIntent,
  saveIntent,
  createIntent,
  deleteIntent,
  IntentFile
} from '@/api/api' // Переконайтеся, що шлях до api.ts правильний

export default function Intents() {
  const [intents, setIntents] = useState<IntentFile[]>([])
  const [selectedFile, setSelectedFile] = useState<string | null>(null)
  const [fileContent, setFileContent] = useState<string>('')
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [isSaving, setIsSaving] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  // Завантаження списку інтентів при першому рендері
  useEffect(() => {
    fetchIntents()
  }, [])

  const fetchIntents = async () => {
    try {
      setIsLoading(true)
      setError(null)
      const files = await listIntents()
      setIntents(files)
    } catch (err) {
      console.error(err)
      setError('Failed to load intents list.')
    } finally {
      setIsLoading(false)
    }
  }

  // Обробник вибору файлу
  const handleSelectFile = async (fname: string) => {
    if (isSaving) return; // Не дозволяти перемикатися під час збереження
    try {
      setIsLoading(true)
      setError(null)
      const content = await getIntent(fname)
      setSelectedFile(content.name)
      setFileContent(content.text)
    } catch (err) {
      console.error(err)
      setError('Failed to load file content.')
      setSelectedFile(null)
      setFileContent('')
    } finally {
      setIsLoading(false)
    }
  }

  // Обробник збереження
  const handleSave = async () => {
    if (!selectedFile) return;

    try {
      setIsSaving(true)
      setError(null)
      await saveIntent(selectedFile, fileContent)
      // Можна додати сповіщення про успішне збереження
    } catch (err) {
      console.error(err)
      setError('Failed to save file.')
    } finally {
      setIsSaving(false)
    }
  }

  // Обробник створення нового файлу
  const handleNew = async () => {
    const name = window.prompt('Enter new intent file name (e.g., "greetings" or "greetings.yml"):')
    if (!name) return;

    try {
      setIsLoading(true)
      setError(null)
      const newFile = await createIntent(name)
      await fetchIntents() // Оновити список
      handleSelectFile(newFile.name) // Вибрати новий файл
    } catch (err) {
      console.error(err)
      setError('Failed to create new file. It might already exist.')
    } finally {
      setIsLoading(false)
    }
  }

  // Обробник видалення
  const handleDelete = async () => {
    if (!selectedFile) return;
    if (!window.confirm(`Are you sure you want to delete ${selectedFile}?`)) return;

    try {
      setIsLoading(true)
      setError(null)
      await deleteIntent(selectedFile)
      setSelectedFile(null)
      setFileContent('')
      await fetchIntents() // Оновити список
    } catch (err) {
      console.error(err)
      setError('Failed to delete file.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div>
      <Header title="Intents" />

      {error && (
        <Card>
          <div className="text-red-500 font-semibold">{error}</div>
        </Card>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Колонка зі списком файлів */}
        <div className="md:col-span-1">
          <Card>
            <button
              onClick={handleNew}
              className="w-full bg-blue-500 hover:bg-blue-600 text-white font-bold py-2 px-4 rounded-lg mb-4"
            >
              New Intent
            </button>
            <div className="max-h-[70vh] overflow-y-auto">
              {isLoading && intents.length === 0 ? (
                <p>Loading...</p>
              ) : (
                intents.map((file) => (
                  <div
                    key={file.name}
                    onClick={() => handleSelectFile(file.name)}
                    className={`p-2 rounded-lg cursor-pointer hover:bg-gray-700 ${
                      selectedFile === file.name ? 'bg-gray-700 font-bold' : ''
                    }`}
                  >
                    {file.name}
                  </div>
                ))
              )}
            </div>
          </Card>
        </div>

        {/* Колонка з редактором */}
        <div className="md:col-span-2">
          {selectedFile ? (
            <Card>
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-semibold">{selectedFile}</h2>
                <div>
                  <button
                    onClick={handleDelete}
                    className="bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded-lg mr-2"
                    disabled={isSaving || isLoading}
                  >
                    Delete
                  </button>
                  <button
                    onClick={handleSave}
                    className="bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded-lg"
                    disabled={isSaving || isLoading}
                  >
                    {isSaving ? 'Saving...' : 'Save'}
                  </button>
                </div>
              </div>
              <textarea
                value={fileContent}
                onChange={(e) => setFileContent(e.target.value)}
                className="w-full h-[70vh] p-2 font-mono text-sm bg-gray-900 border border-gray-700 rounded-lg text-white"
                placeholder="File content will appear here..."
                disabled={isLoading}
              />
            </Card>
          ) : (
            <Card>
              <div className="flex items-center justify-center h-[70vh]">
                <p className="text-gray-400">
                  Select an intent from the list to edit, or create a new one.
                </p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}