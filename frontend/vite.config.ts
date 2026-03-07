import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  // 预构建大依赖，加速 dev 刷新
  optimizeDeps: {
    include: [
      'react',
      'react-dom',
      'react-router-dom',
      'recharts',
      'framer-motion',
      'lucide-react',
      'axios',
      'dompurify',
    ],
  },
  server: {
    // 预热常用文件
    warmup: {
      clientFiles: [
        './src/App.tsx',
        './src/pages/DataManagement.tsx',
        './src/pages/AnalysisResult.tsx',
        './src/components/Layout.tsx',
      ],
    },
  },
})
