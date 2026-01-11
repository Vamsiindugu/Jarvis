// File: vite.config.js - Purpose: This file handles Vite.Config functionality.
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    base: './', // Important for Electron
    server: {
        port: 5173,
    }
})
