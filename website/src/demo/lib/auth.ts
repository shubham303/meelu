export interface MeeluSession {
  created: boolean;
}

export class AuthFailure extends Error {
  constructor(
    message: string,
    readonly code: string | null,
  ) {
    super(message);
  }
}

const pause = () => new Promise((resolve) => setTimeout(resolve, 400));

function requireEmail(email: string): void {
  if (!email.includes("@")) throw new AuthFailure("Enter a valid email address.", "INVALID_EMAIL");
}

function requireCode(otp: string): void {
  if (!/^\d{6}$/.test(otp.trim())) throw new AuthFailure("Enter the 6-digit code. In the demo any six digits work.", "INVALID_OTP");
}

export async function signInWithPassword(email: string, password: string): Promise<MeeluSession> {
  requireEmail(email);
  if (!password) throw new AuthFailure("Enter your password. In the demo any password works.", "INVALID_PASSWORD");
  await pause();
  return { created: false };
}

export async function signUpWithPassword(_name: string, email: string, password: string): Promise<void> {
  requireEmail(email);
  if (password.length < 8) throw new AuthFailure("Use at least 8 characters.", "PASSWORD_TOO_SHORT");
  await pause();
}

export async function verifyEmailCode(email: string, otp: string): Promise<MeeluSession> {
  requireEmail(email);
  requireCode(otp);
  await pause();
  return { created: true };
}

export async function resendVerificationCode(email: string): Promise<void> {
  requireEmail(email);
  await pause();
}

export async function requestPasswordReset(email: string): Promise<void> {
  requireEmail(email);
  await pause();
}

export async function resetPasswordWithCode(email: string, otp: string, password: string): Promise<MeeluSession> {
  requireEmail(email);
  requireCode(otp);
  if (password.length < 8) throw new AuthFailure("Use at least 8 characters.", "PASSWORD_TOO_SHORT");
  await pause();
  return { created: false };
}

export async function signOutEverywhere(): Promise<void> {
  await pause();
}
