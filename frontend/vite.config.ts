/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import type { UserConfig } from 'vitest/config'
import path from 'path'
import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'


function figmaAssetResolver() {
  return {
    name: 'figma-asset-resolver',
    resolveId(id: string) {
      if (id.startsWith('figma:asset/')) {
        const filename = id.replace('figma:asset/', '')
        return path.resolve(__dirname, 'src/assets', filename)
      }
    },
  }
}

export default defineConfig({
  plugins: [
    figmaAssetResolver(),
    // The React and Tailwind plugins are both required for Make, even if
    // Tailwind is not being actively used – do not remove them
    react(),
    tailwindcss(),
  ],
  resolve: {
    alias: {
      // Alias @ to the src directory
      '@': path.resolve(__dirname, './src'),
    },
  },

  // Em desenvolvimento o front chama /api e /health como caminhos relativos e o
  // Vite encaminha para a API. Assim não há URL de back-end espalhada no código
  // nem CORS para configurar durante o desenvolvimento.
  server: {
    port: 5173,
    proxy: {
      '/api': { target: process.env.VITE_API_TARGET ?? 'http://localhost:8000', changeOrigin: true },
      '/health': { target: process.env.VITE_API_TARGET ?? 'http://localhost:8000', changeOrigin: true },
    },
  },

  preview: {
    port: 4173,
    proxy: {
      '/api': { target: process.env.VITE_API_TARGET ?? 'http://localhost:8000', changeOrigin: true },
      '/health': { target: process.env.VITE_API_TARGET ?? 'http://localhost:8000', changeOrigin: true },
    },
  },

  // File types to support raw imports. Never add .css, .tsx, or .ts files to this.
  assetsInclude: ['**/*.svg', '**/*.csv'],

  // Os testes cobrem o que quebraria a demonstração: o cliente HTTP (contrato com
  // a API) e as telas onde uma regra de negócio vira decisão de interface.
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    css: false,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html', 'json-summary'],
      include: ['src/app/api/**/*.ts', 'src/app/pages/**/*.tsx', 'src/app/components/AsyncBoundary.tsx'],
      // `types.ts` só declara tipos: não sobra runtime para cobrir, e mantê-lo
      // no denominador só distorceria o número.
      exclude: ['src/app/components/ui/**', 'src/app/components/figma/**',
                'src/app/api/types.ts'],
      // Um limiar que ninguém verifica não é um limiar: `npm run coverage`
      // reprova sozinho se a cobertura cair.
      thresholds: { lines: 70, functions: 60, statements: 70 },
    },
  },
} as UserConfig)
