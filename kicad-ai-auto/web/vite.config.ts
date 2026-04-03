import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/kicad-ipc': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
  build: {
    // 设置chunk大小警告阈值
    chunkSizeWarningLimit: 400,
    rollupOptions: {
      output: {
        // 更细粒度的代码分割
        manualChunks: (id) => {
          // React 核心库
          if (id.includes('node_modules/react/') || id.includes('node_modules/react-dom/') || id.includes('node_modules/react-router-dom/')) {
            return 'vendor-react';
          }
          // Three.js 核心 (最大的库，需要单独分割)
          if (id.includes('node_modules/three/') && !id.includes('examples/')) {
            return 'vendor-three-core';
          }
          // Three.js 示例/插件 (OrbitControls等)
          if (id.includes('node_modules/three/examples/')) {
            return 'vendor-three-addons';
          }
          // React Three Fiber/Drei
          if (id.includes('node_modules/@react-three/')) {
            return 'vendor-r3f';
          }
          // Konva 画布库
          if (id.includes('node_modules/konva/') || id.includes('node_modules/react-konva/')) {
            return 'vendor-konva';
          }
          // Radix UI 组件
          if (id.includes('node_modules/@radix-ui/')) {
            return 'vendor-radix';
          }
          // Heroicons
          if (id.includes('node_modules/@heroicons/')) {
            return 'vendor-heroicons';
          }
          // Headless UI
          if (id.includes('node_modules/@headlessui/')) {
            return 'vendor-headlessui';
          }
          // Zustand 状态管理
          if (id.includes('node_modules/zustand/')) {
            return 'vendor-zustand';
          }
          // 其他大型node_modules
          if (id.includes('node_modules/')) {
            return 'vendor-misc';
          }
        },
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    exclude: [
      '**/node_modules/**',
      '**/e2e/**',
      '**/test-pcb-resize.spec.ts',
    ],
  },
})
