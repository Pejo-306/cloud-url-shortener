import { CognitoUserPool, CognitoUser, AuthenticationDetails, CognitoUserAttribute } from 'amazon-cognito-identity-js'

import config from '@/config'

const userPool = new CognitoUserPool({
  UserPoolId: config.aws.cognito.userPoolId,
  ClientId: config.aws.cognito.clientId,
})

export const isAuthenticated = () => {
  const accessToken = localStorage.getItem('session.accessToken')
  const idToken = localStorage.getItem('session.idToken')
  const refreshToken = localStorage.getItem('session.refreshToken')
  const expiresAt = Number(localStorage.getItem('session.expiresAt'))

  clearSession()

  if (Date.now() >= expiresAt) {
    clearSession()
    return false
  }
  return accessToken && idToken && refreshToken && expiresAt
}

export const persistSession = (session) => {
  const expiresAt = Date.now() + session.expiresIn

  localStorage.setItem('session.accessToken', session.accessToken)
  localStorage.setItem('session.idToken', session.idToken)
  localStorage.setItem('session.refreshToken', session.refreshToken)
  localStorage.setItem('session.expiresAt', String(expiresAt))
}

export const clearSession = () => {
  localStorage.removeItem('session.accessToken')
  localStorage.removeItem('session.idToken')
  localStorage.removeItem('session.refreshToken')
  localStorage.removeItem('session.expiresAt')
}

export const login = (email, password) => {
  const authDetails = new AuthenticationDetails({
    Username: email,
    Password: password,
  })
  const user = new CognitoUser({
    Username: email,
    Pool: userPool,
  })

  return new Promise((resolve, reject) => {
    user.authenticateUser(authDetails, {
      onSuccess: (session) => {
        resolve({
          accessToken: session.getAccessToken().getJwtToken(),
          idToken: session.getIdToken().getJwtToken(),
          refreshToken: session.getRefreshToken().getToken(),
          expiresIn: session.getAccessToken().getExpiration(),  // in seconds
        })
      },
      onFailure: (err) => reject(err)
    })
  })
}

export const register = (email, password) => {
  return new Promise((resolve, reject) => {
    const attributes = [
      new CognitoUserAttribute({ Name: 'email', Value: email }),
    ]

    userPool.signUp(email, password, attributes, null, (err, result) => {
      if (err) return reject(err)
      resolve(result)
    })
  })
}

export const confirmRegistration = (email, code) => {
  return new Promise((resolve, reject) => {
    const user = new CognitoUser({ Username: email, Pool: userPool })

    user.confirmRegistration(code, true, (err, result) => {
      if (err) return reject(err)
      resolve(result)
    })
  })
}

export const resendConfirmationCode = (email) => {
  return new Promise((resolve, reject) => {
    const user = new CognitoUser({ Username: email, Pool: userPool })

    user.resendConfirmationCode((err, result) => {
      if (err) return reject(err)
      resolve(result)
    })
  })
}

export const resetPassword = (email, newPassword) => {
  console.log('resetPassword triggered with: ', email, newPassword)
}

export const logout = () => {
  console.log('logout triggered')
}
