import { api } from '@/lib/api'
import type { SettingsApplyResponse } from '@/lib/types'

export type ApplyModelOptions = {
  model?: string
  small_model?: string
  base_url?: string
  api_key?: string
  keys?: Record<string, string>
}

/** Sole writer to POST /api/settings — catalog, form, and model chip all use this. */
export async function applyModel(opts: ApplyModelOptions): Promise<SettingsApplyResponse> {
  const body: Record<string, unknown> = {}
  if (opts.model !== undefined) body.model = opts.model
  if (opts.small_model !== undefined) body.small_model = opts.small_model
  if (opts.base_url !== undefined) body.base_url = opts.base_url
  if (opts.api_key) body.api_key = opts.api_key
  if (opts.keys && Object.keys(opts.keys).length > 0) body.keys = opts.keys
  return api.settings(body)
}
