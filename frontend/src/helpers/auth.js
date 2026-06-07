import {
  CognitoUserPool,
  CognitoUser,
  AuthenticationDetails,
  CognitoUserAttribute,
} from 'amazon-cognito-identity-js'

import config from '@/config'
import { clearSession } from '@/helpers/session'

const userPool = new CognitoUserPool({
  UserPoolId: config.aws.cognito.userPoolId,
  ClientId: config.aws.cognito.clientId,
})

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
          expiresIn: session.getAccessToken().getExpiration(), // in seconds
        })
      },
      onFailure: (err) => reject(err),
    })
  })
}

export const register = (email, password) => {
  return new Promise((resolve, reject) => {
    const attributes = [new CognitoUserAttribute({ Name: 'email', Value: email })]

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

export const requestPasswordReset = (email) => {
  return new Promise((resolve, reject) => {
    const user = new CognitoUser({ Username: email, Pool: userPool })

    user.forgotPassword({
      onSuccess: (result) => resolve(result),
      onFailure: (err) => reject(err),
    })
  })
}

export const confirmPasswordReset = (email, code, newPassword) => {
  return new Promise((resolve, reject) => {
    const user = new CognitoUser({ Username: email, Pool: userPool })

    user.confirmPassword(code, newPassword, {
      onSuccess: (result) => resolve(result),
      onFailure: (err) => reject(err),
    })
  })
}

export const logout = () => {
  clearSession()
}
