/// <reference types="vite/client" />

/** Biến môi trường của dashboard — mọi biến phải có tiền tố `VITE_` mới lọt ra client. */
interface ImportMetaEnv {
  /** Địa chỉ gateway. Mọi lời gọi API đi qua đây, không gọi thẳng java-core/ai-service. */
  readonly VITE_GATEWAY_URL: string
  readonly VITE_WS_URL: string
  readonly VITE_APP_NAME: string
  /** `'true'` thì bật tầng mock MSW thay cho backend thật. */
  readonly VITE_USE_MOCK?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
