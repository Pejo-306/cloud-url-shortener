import { createApp } from 'vue'

import '@/assets/css/global.css'
import '@/assets/css/auth-forms.css'

import App from '@/App.vue'
import router from '@/router'

createApp(App).use(router).mount('#app')
