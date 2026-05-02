import { mount } from 'svelte'
import './app.css'
import App from './App.svelte'

if (import.meta.env.DEV) {
  const { installDevLog } = await import('./lib/dev-log')
  installDevLog()
}

const app = mount(App, {
  target: document.getElementById('app')!,
})

export default app
