const configModules = import.meta.glob('../config/*/app.config.json', { eager: true })

const configs = {}
for (const path in configModules) {
  const folderName = path.split('/').slice(-2, -1)[0]
  const module = configModules[path]
  configs[folderName] = module?.default ?? module
}

export function getCurrentConfig() {
  const mode = import.meta.env.MODE || 'local'
  return configs[mode] || configs.local
}

export default getCurrentConfig()
