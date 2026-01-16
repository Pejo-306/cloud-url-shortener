const configModules = import.meta.glob('../config/*/app.config.json', { eager: true })

const configs = {}
for (const path in configModules) {
  const folderName = path.split('/')[2]
  configs[folderName] = configModules[path]
}

export function getCurrentConfig() {
  const mode = import.meta.env.MODE || 'local'
  return configs[mode] || configs.local
}

export default getCurrentConfig()
