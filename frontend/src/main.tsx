import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import { AuthProvider } from './auth';
import { ApiError } from './api';
import './styles.css';

const client = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30000,
      retry: (count, error) =>
        !(error instanceof ApiError && [401, 403].includes(error.status)) && count < 1,
      refetchOnWindowFocus: false,
    },
    mutations: { retry: false },
  },
});
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={client}>
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
