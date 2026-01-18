import config from '@/config'

export const validateUrl = (url) => {
  // prettier-ignore
  const urlPattern = /^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$/
  return urlPattern.test(url)
}

export const validateEmail = (email) => {
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  const valid = emailPattern.test(email)
  const message = valid ? null : config.auth.errorMessages.invalidEmail
  return { valid, message }
}

export const validatePassword = (password) => {
  if (password.length < config.auth.passwordPolicy.minLength) {
    return { valid: false, message: config.auth.errorMessages.passwordTooShort }
  }
  if (config.auth.passwordPolicy.requireUppercase && !password.match(/[A-Z]/)) {
    return { valid: false, message: config.auth.errorMessages.passwordRequiresUppercase }
  }
  if (config.auth.passwordPolicy.requireLowercase && !password.match(/[a-z]/)) {
    return { valid: false, message: config.auth.errorMessages.passwordRequiresLowercase }
  }
  if (config.auth.passwordPolicy.requireNumbers && !password.match(/[0-9]/)) {
    return { valid: false, message: config.auth.errorMessages.passwordRequiresNumbers }
  }
  if (config.auth.passwordPolicy.requireSymbols && !password.match(/[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/)) {
    return { valid: false, message: config.auth.errorMessages.passwordRequiresSymbols }
  }
  return { valid: true, message: null }
}

export const validatePasswordConfirmation = (password, passwordConfirm) => {
  if (password !== passwordConfirm) {
    return { valid: false, message: config.auth.errorMessages.passwordConfirmationMismatch }
  }
  return { valid: true, message: null }
}
