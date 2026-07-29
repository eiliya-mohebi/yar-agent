import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { PageHead } from '@/components/layout/PageHead'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { useEditing } from '@/hooks/useEditing'
import { useLang } from '@/hooks/useLang'
import { api } from '@/lib/api'
import { applyModel } from '@/lib/settings'
import type { DashboardData, ModelCatalog, PinAction } from '@/lib/types'
import { cn } from '@/lib/utils'

type Props = {
  data: DashboardData | null
  agoSec: number | null
  error?: string | null
  onRefresh: () => Promise<void>
}

function PinStar({
  pinned,
  id,
  onPin,
}: {
  pinned: boolean
  id: string
  onPin: (id: string, action: PinAction) => void
}) {
  const { t } = useLang()
  return (
    <button
      type="button"
      className={cn(
        'cursor-pointer border-0 bg-transparent p-0 text-[15px] leading-none',
        pinned ? 'text-[var(--warn)]' : 'text-[var(--ink3)]',
      )}
      title={pinned ? t.unpinTitle : t.pinTitle}
      aria-label={pinned ? t.unpinTitle : t.pinTitle}
      onClick={() => onPin(id, pinned ? 'unpin' : 'pin')}
    >
      {pinned ? '★' : '☆'}
    </button>
  )
}

export function SettingsPage({ data, agoSec, error, onRefresh }: Props) {
  const { t, toggleLang } = useLang()
  const { editing, markEditing, clearEditing } = useEditing()

  const [model, setModel] = useState('')
  const [smallModel, setSmallModel] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [searchKey, setSearchKey] = useState('')
  const [addId, setAddId] = useState('')
  const [catalogFilter, setCatalogFilter] = useState('')
  const [catalog, setCatalog] = useState<ModelCatalog | null>(null)
  const [msg, setMsg] = useState('')
  const [switchMsg, setSwitchMsg] = useState('')

  const st = data?.settings
  const pinnedIds = new Set((st?.pinned ?? []).map((p) => p.id))

  const loadCatalog = useCallback(async () => {
    try {
      setCatalog(await api.models())
    } catch {
      setCatalog({
        models: [],
        listed: false,
        endpoint: '',
        model: '',
        small_model: '',
        pinned: [],
      })
    }
  }, [])

  useEffect(() => {
    void loadCatalog()
  }, [loadCatalog])

  useEffect(() => {
    if (editing || !st) return
    setModel(st.model)
    setSmallModel(st.small_model)
    setBaseUrl(st.base_url)
  }, [st, editing])

  const handlePin = useCallback(
    async (id: string, action: PinAction) => {
      setMsg('')
      const r = await api.pin({ action, id })
      if (r.error) {
        setMsg(r.error)
        return
      }
      clearEditing()
      await onRefresh()
      void loadCatalog()
    },
    [clearEditing, loadCatalog, onRefresh],
  )

  const switchModel = useCallback(
    async (id: string, asGate = false) => {
      if (!st) return
      setSwitchMsg(t.switching)
      const r = await applyModel({
        model: asGate ? st.model : id,
        small_model: asGate ? id : st.small_model,
      })
      if (r.error) {
        setSwitchMsg(r.error)
        return
      }
      setSwitchMsg(asGate ? t.gateNow(id) : t.modelNow(id))
      clearEditing()
      await onRefresh()
      void loadCatalog()
    },
    [clearEditing, loadCatalog, onRefresh, st, t],
  )

  const handleSave = async (e: FormEvent) => {
    e.preventDefault()
    setMsg(t.switching)
    const keys: Record<string, string> = {}
    if (searchKey.trim()) keys.TAVILY_API_KEY = searchKey.trim()
    const r = await applyModel({
      model: model.trim(),
      small_model: smallModel.trim(),
      base_url: baseUrl.trim(),
      api_key: apiKey.trim() || undefined,
      keys: Object.keys(keys).length > 0 ? keys : undefined,
    })
    if (r.error) {
      setMsg(r.error)
      return
    }
    setMsg(t.switchedTo(r.model || model.trim()))
    clearEditing()
    setApiKey('')
    setSearchKey('')
    await onRefresh()
    void loadCatalog()
  }

  const filteredCatalog =
    catalog?.models.filter((m) => {
      const q = catalogFilter.trim().toLowerCase()
      return !q || m.id.toLowerCase().includes(q)
    }) ?? []

  const addPinned = async () => {
    const id = addId.trim()
    if (!id) return
    await handlePin(id, 'pin')
    setAddId('')
  }

  if (error && !data) {
    return (
      <>
        <PageHead title={t.settings} agoSec={agoSec} />
        <p className="text-[var(--bad)]">{error}</p>
      </>
    )
  }

  return (
    <>
      <PageHead title={t.settings} home={data?.home} agoSec={agoSec} />

      <h2 className="mb-2 text-[11px] font-semibold tracking-[0.09em] text-[var(--ink2)] uppercase">
        {t.currentModels}
      </h2>
      <div className="mb-6 rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3.5">
        <div className="flex flex-wrap gap-x-6 gap-y-2 text-[13px]">
          <div>
            <span className="text-[var(--ink2)]">{t.loopModel}: </span>
            <code className="font-mono" dir="ltr">
              {data?.model ?? st?.model ?? '…'}
            </code>
          </div>
          <div>
            <span className="text-[var(--ink2)]">{t.smallModel}: </span>
            <code className="font-mono" dir="ltr">
              {st?.small_model ?? '…'}
            </code>
          </div>
        </div>
      </div>

      <h2 className="mb-2 text-[11px] font-semibold tracking-[0.09em] text-[var(--ink2)] uppercase">
        {t.yourModels}{' '}
        <span className="font-normal normal-case tracking-normal text-[var(--ink3)]">
          — {t.yourModelsSub}
        </span>
      </h2>
      <div className="mb-6 rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3.5">
        {(st?.pinned ?? []).length ? (
          <div className="space-y-2">
            {(st?.pinned ?? []).map((p) => {
              const active = p.id === data?.model
              return (
                <div
                  key={p.id}
                  className={cn(
                    'flex flex-wrap items-center gap-2 rounded-md border border-[var(--line)] px-2.5 py-2',
                    active && 'border-[var(--accent)] bg-[var(--accent-soft)]',
                  )}
                >
                  <PinStar pinned id={p.id} onPin={handlePin} />
                  <code className="min-w-0 flex-1 break-all font-mono text-[13px]" dir="ltr">
                    {p.id}
                  </code>
                  {p.default ? (
                    <span className="rounded-full border border-[var(--line2)] px-2 py-0.5 text-[11px] text-[var(--ink2)]">
                      default
                    </span>
                  ) : (
                    <button
                      type="button"
                      className="cursor-pointer border-0 bg-transparent p-0 text-[12px] text-[var(--accent)] underline-offset-2 hover:underline"
                      onClick={() => void handlePin(p.id, 'default')}
                    >
                      {t.makeDefault}
                    </button>
                  )}
                  <button
                    type="button"
                    className="cursor-pointer border-0 bg-transparent p-0 text-[12px] text-[var(--ink3)] underline-offset-2 hover:underline"
                    onClick={() => void handlePin(p.id, 'unpin')}
                  >
                    {t.remove}
                  </button>
                </div>
              )
            })}
          </div>
        ) : (
          <p className="text-[13px] text-[var(--ink3)]">{t.noPins}</p>
        )}
        <div className="mt-3 flex flex-wrap items-end gap-2">
          <div className="min-w-[200px] flex-1">
            <label className="mb-1 block text-[11.5px] text-[var(--ink2)]">{t.addModel}</label>
            <Input
              value={addId}
              dir="ltr"
              placeholder="gpt-4.1-mini"
              onFocus={markEditing}
              onChange={(e) => {
                markEditing()
                setAddId(e.target.value)
              }}
            />
          </div>
          <Button type="button" size="sm" onClick={() => void addPinned()}>
            {t.add}
          </Button>
        </div>
      </div>

      <form
        className="mb-6 rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3.5"
        onSubmit={(e) => void handleSave(e)}
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <div>
            <label className="mb-1 block text-[11.5px] text-[var(--ink2)]">{t.loopModel}</label>
            <Input
              value={model}
              dir="ltr"
              onFocus={markEditing}
              onChange={(e) => {
                markEditing()
                setModel(e.target.value)
              }}
            />
          </div>
          <div>
            <label className="mb-1 block text-[11.5px] text-[var(--ink2)]">{t.smallModel}</label>
            <Input
              value={smallModel}
              dir="ltr"
              onFocus={markEditing}
              onChange={(e) => {
                markEditing()
                setSmallModel(e.target.value)
              }}
            />
          </div>
          <div className="sm:col-span-2">
            <label className="mb-1 block text-[11.5px] text-[var(--ink2)]">{t.baseUrl}</label>
            <Input
              value={baseUrl}
              dir="ltr"
              placeholder="https://api.avalai.ir/v1"
              onFocus={markEditing}
              onChange={(e) => {
                markEditing()
                setBaseUrl(e.target.value)
              }}
            />
            <p className="mt-1 text-[11.5px] text-[var(--ink3)]">{t.baseUrlHint}</p>
          </div>
          <div>
            <label className="mb-1 block text-[11.5px] text-[var(--ink2)]">{t.apiKey}</label>
            <Input
              type="password"
              value={apiKey}
              dir="ltr"
              autoComplete="off"
              placeholder={
                st?.api_key_set && st.api_key_last4
                  ? t.keySet(st.api_key_last4)
                  : t.keyUnset
              }
              onFocus={markEditing}
              onChange={(e) => {
                markEditing()
                setApiKey(e.target.value)
              }}
            />
          </div>
          <div>
            <label className="mb-1 block text-[11.5px] text-[var(--ink2)]">{t.searchKey}</label>
            <Input
              type="password"
              value={searchKey}
              dir="ltr"
              autoComplete="off"
              placeholder={
                st?.search_key_set && st.search_key_last4
                  ? t.keySet(st.search_key_last4)
                  : t.keyUnset
              }
              onFocus={markEditing}
              onChange={(e) => {
                markEditing()
                setSearchKey(e.target.value)
              }}
            />
            <p className="mt-1 text-[11.5px] text-[var(--ink3)]">{t.searchKeyHint}</p>
          </div>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-2">
          <Button type="submit" size="sm">
            {t.save}
          </Button>
          <Button type="button" variant="outline" size="sm" onClick={toggleLang}>
            {t.langToggle}
          </Button>
          {msg ? (
            <span className="text-[12.5px] text-[var(--ink2)]" dir="auto">
              {msg}
            </span>
          ) : null}
        </div>
      </form>

      {catalog?.listed && catalog.models.length > 0 ? (
        <>
          <h2 className="mb-2 text-[11px] font-semibold tracking-[0.09em] text-[var(--ink2)] uppercase">
            {t.catalog}
          </h2>
          <div className="rounded-lg border border-[var(--line)] bg-[var(--panel)] px-4 py-3.5">
            <p className="mb-2 text-[12px] text-[var(--ink3)]">
              {t.modelsOn(catalog.models.length, catalog.endpoint)}
            </p>
            <Input
              value={catalogFilter}
              dir="ltr"
              placeholder={t.catalogFilter}
              className="mb-3"
              onFocus={markEditing}
              onChange={(e) => {
                markEditing()
                setCatalogFilter(e.target.value)
              }}
            />
            <div className="max-h-[360px] space-y-1 overflow-y-auto">
              {filteredCatalog.map((m) => {
                const isCurrent = m.id === st?.model
                const isGate = m.id === st?.small_model
                const isPinned = pinnedIds.has(m.id)
                return (
                  <div
                    key={m.id}
                    className="flex flex-wrap items-center gap-2 rounded-md border border-[var(--line)] px-2 py-1.5 text-[13px]"
                  >
                    <PinStar pinned={isPinned} id={m.id} onPin={handlePin} />
                    <button
                      type="button"
                      className="min-w-0 flex-1 cursor-pointer border-0 bg-transparent p-0 text-start font-mono hover:text-[var(--accent)]"
                      dir="ltr"
                      onClick={() => void switchModel(m.id)}
                    >
                      {m.id}
                    </button>
                    {isGate ? (
                      <span className="rounded-full border border-[var(--line2)] px-2 py-0.5 text-[11px]">
                        {t.gateLabel}
                      </span>
                    ) : (
                      <button
                        type="button"
                        className="cursor-pointer border-0 bg-transparent p-0 text-[12px] text-[var(--accent)]"
                        onClick={() => void switchModel(m.id, true)}
                      >
                        {t.useAsGate}
                      </button>
                    )}
                    {isCurrent ? (
                      <span className="rounded-full border border-[var(--good)] bg-[var(--good-soft)] px-2 py-0.5 text-[11px] text-[var(--good)]">
                        {t.current}
                      </span>
                    ) : (
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="h-7 px-2 text-[11px]"
                        onClick={() => void switchModel(m.id)}
                      >
                        {t.useModel}
                      </Button>
                    )}
                  </div>
                )
              })}
            </div>
            {switchMsg ? (
              <p className="mt-2 text-[12px] text-[var(--ink2)]" dir="auto">
                {switchMsg}
              </p>
            ) : null}
          </div>
        </>
      ) : catalog?.error ? (
        <p className="text-[12px] text-[var(--ink3)]">{t.modelListUnavailable(catalog.error)}</p>
      ) : null}
    </>
  )
}
