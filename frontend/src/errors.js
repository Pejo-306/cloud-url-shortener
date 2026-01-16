export class BackendError extends Error {
  /**
   * @param {number} status
   * @param {string} message
   * @param {string} errorCode
   */
  constructor(status, message, errorCode) {
    super(message)
    this.name = 'BackendError'
    this.status = status
    this.errorCode = errorCode

    Object.setPrototypeOf(this, new.target.prototype)
  }

  toJSON() {
    return {
      message: this.message,
      errorCode: this.errorCode,
    }
  }
}
