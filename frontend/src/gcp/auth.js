import { initializeApp } from 'firebase/app'
import {
  getAuth,
  createUserWithEmailAndPassword,
  sendEmailVerification,
  sendPasswordResetEmail,
  signInWithEmailAndPassword,
  signOut,
} from 'firebase/auth'

import config from '@/config'
import { clearSession } from '@/helpers/session'

let app = null
let auth = null

function getFirebaseApp() {
  if (app) {
    return app
  }

  app = initializeApp({
    apiKey: config.gcp.identityPlatform.webApiKey,
    authDomain: config.gcp.identityPlatform.authDomain,
    projectId: config.gcp.projectId,
  })
  return app
}

function getFirebaseAuth() {
  if (auth) {
    return auth
  }

  auth = getAuth(getFirebaseApp())
  return auth
}

const getActionCodeSettings = () => ({
  url: `${window.location.origin}/auth/action`,
})

const toSession = async (user) => {
  const idToken = await user.getIdToken()
  const idTokenResult = await user.getIdTokenResult()

  return {
    accessToken: idToken,
    idToken,
    refreshToken: user.refreshToken,
    expiresIn: Date.parse(idTokenResult.expirationTime) - Date.now(),
  }
}

export const login = async (email, password) => {
  const { user } = await signInWithEmailAndPassword(getFirebaseAuth(), email, password)
  return toSession(user)
}

export const register = async (email, password) => {
  const { user } = await createUserWithEmailAndPassword(getFirebaseAuth(), email, password)
  await sendEmailVerification(user, getActionCodeSettings())
  await signOut(getFirebaseAuth())

  return {
    userConfirmed: user.emailVerified,
  }
}

export const resendConfirmationCode = async (email, password) => {
  const { user } = await signInWithEmailAndPassword(getFirebaseAuth(), email, password)
  await sendEmailVerification(user, getActionCodeSettings())
  await signOut(getFirebaseAuth())
}

export const requestPasswordReset = (email) => {
  return sendPasswordResetEmail(getFirebaseAuth(), email, getActionCodeSettings())
}

export const logout = () => {
  clearSession()
  return signOut(getFirebaseAuth())
}
