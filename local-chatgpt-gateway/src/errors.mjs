import { ChatGPTError } from '@siwc/local';

export class GatewayError extends ChatGPTError {}

const statuses = {
  sign_in_required: 401, invalid_refresh_token: 401, refresh_token_expired: 401,
  refresh_token_invalidated: 401, refresh_token_reused: 401, token_expired: 401,
  sharing_not_enabled: 403, subscription_sharing_user_not_eligible: 403,
  subscription_sharing_route_not_supported: 403, subscription_sharing_invalid_user: 401,
  chatpass_v2_scope_not_authorized: 403, chatpass_v2_invalid_authorization_context: 403,
  subscription_sharing_v2_user_not_eligible: 403, subscription_sharing_v2_route_not_supported: 403,
  subscription_sharing_usage_limit_exceeded: 429, subscription_sharing_usage_unavailable: 503,
  subscription_sharing_user_unavailable: 503, subscription_sharing_v2_user_unavailable: 503,
  subscription_sharing_unsupported_capability: 400, model_not_found: 400,
  network_error: 502, stream_interrupted: 502, invalid_stream: 502,
  response_incomplete: 502, empty_response: 502, cancelled: 504,
  identity_verification_unavailable: 503, refresh_not_ready: 503,
};

export function publicError(error) {
  if (!(error instanceof ChatGPTError)) return {
    status: 500, body: { error: { code: 'internal_error', message: 'Local gateway failed. No credentials were logged.', retryable: false } },
  };
  // Stream-layer failures often carry HTTP 200: keep that diagnostic but return an error locally.
  const status = error.status >= 400 && error.status <= 599 ? error.status : statuses[error.code] ?? 502;
  const detail = { ...error.toJSON(), ...(!(error instanceof GatewayError) && error.status !== undefined ? { upstream_status: error.status } : {}) };
  delete detail.status;
  if (error.code === 'subscription_sharing_usage_limit_exceeded') {
    detail.message = 'ChatGPT plan or application usage limit reached. Review ChatGPT Settings > Usage; no billing fallback is used.';
    detail.usage_url = 'https://chatgpt.com/settings/usage';
  }
  return { status, body: { error: detail } };
}
