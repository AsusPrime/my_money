import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import './index.css'
import App from './App.tsx'
import { GlobalProgressBar } from './components/GlobalProgressBar.tsx'

const queryClient = new QueryClient()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <GlobalProgressBar />
        <Toaster
          position="bottom-right"
          toastOptions={{
            style: {
              background: '#181a20',
              color: '#eaecee',
              border: '1px solid #2b3139',
            },
            success: { iconTheme: { primary: '#0ecb81', secondary: '#181a20' } },
            error: { iconTheme: { primary: '#f6465d', secondary: '#181a20' } },
          }}
        />
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
