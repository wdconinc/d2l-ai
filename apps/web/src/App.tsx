import { useMemo, useState } from 'react'
import type { FormEvent } from 'react'
import './components/result-preview'
import './App.css'
import { t } from './i18n'
import type { Locale } from './i18n'

type Workflow = 'u2' | 'u3'
type BloomLevel = 'remember' | 'understand' | 'apply' | 'analyze'

type PreviewState = {
  title: string
  content: string
  metadata: string
}

type LaunchContext = {
  tenant: string
  course_id: string
  role: string
  deployment_id: string
  [key: string]: unknown
}

const SENSITIVE_KEY_PATTERN = /(token|secret|nonce|jwt|signature|claim|id_token|access_token)/i
const BLOOM_LABEL_KEYS = {
  remember: 'bloomRemember',
  understand: 'bloomUnderstand',
  apply: 'bloomApply',
  analyze: 'bloomAnalyze',
} as const

const countNonEmptyLines = (value: string): number =>
  value
    .split('\n')
    .map((entry) => entry.trim())
    .filter((entry) => entry.length > 0).length

const sanitizeContext = (value: unknown): unknown => {
  if (Array.isArray(value)) {
    return value.map((entry) => sanitizeContext(entry))
  }

  if (value && typeof value === 'object') {
    return Object.entries(value).reduce<Record<string, unknown>>((result, [key, entry]) => {
      if (SENSITIVE_KEY_PATTERN.test(key)) {
        result[key] = '[redacted]'
        return result
      }

      result[key] = sanitizeContext(entry)
      return result
    }, {})
  }

  if (typeof value === 'string' && value.length > 32) {
    return `${value.slice(0, 8)}…${value.slice(-6)}`
  }

  return value
}

const getLaunchContext = (): LaunchContext => {
  const defaultContext: LaunchContext = {
    tenant: 'sandbox.brightspace.com',
    course_id: '12345',
    role: 'Instructor',
    deployment_id: 'sample-deployment-id',
  }

  const runtimeContext = (window as Window & { __LTI_LAUNCH_CONTEXT__?: unknown })
    .__LTI_LAUNCH_CONTEXT__

  if (!runtimeContext || typeof runtimeContext !== 'object') {
    return defaultContext
  }

  return {
    ...defaultContext,
    ...(runtimeContext as Record<string, unknown>),
  }
}

function App() {
  const [locale, setLocale] = useState<Locale>('en')
  const [workflow, setWorkflow] = useState<Workflow>('u2')
  const [u2ModuleTitle, setU2ModuleTitle] = useState('')
  const [u2Topics, setU2Topics] = useState('')
  const [u3Reading, setU3Reading] = useState('')
  const [u3Bloom, setU3Bloom] = useState<BloomLevel>('understand')
  const [u3Count, setU3Count] = useState(5)
  const [preview, setPreview] = useState<PreviewState | null>(null)
  const [showConfirmation, setShowConfirmation] = useState(false)
  const [writeBackStatus, setWriteBackStatus] = useState('')

  const launchContext = useMemo(() => {
    if (!import.meta.env.DEV) {
      return null
    }

    return JSON.stringify(sanitizeContext(getLaunchContext()), null, 2)
  }, [])

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const bloomDisplay = t(locale, BLOOM_LABEL_KEYS[u3Bloom])

    if (workflow === 'u2') {
      const topicCount = countNonEmptyLines(u2Topics)

      setPreview({
        title: t(locale, 'workflowU2Title'),
        content: `${t(locale, 'u2ModuleTitleLabel')}: ${u2ModuleTitle || t(locale, 'previewEmptyValue')}\n${t(locale, 'u2TopicsLabel')}: ${topicCount}`,
        metadata: t(locale, 'previewMetadataU2'),
      })
      setWriteBackStatus('')
      return
    }

    setPreview({
      title: t(locale, 'workflowU3Title'),
      content: `${t(locale, 'u3BloomLabel')}: ${bloomDisplay}\n${t(locale, 'u3CountLabel')}: ${u3Count}\n${t(locale, 'u3ReadingLabel')}: ${u3Reading.slice(0, 120) || t(locale, 'previewEmptyValue')}`,
      metadata: t(locale, 'previewMetadataU3'),
    })
    setWriteBackStatus('')
  }

  return (
    <main className="app-shell">
      <header className="panel">
        <h1>{t(locale, 'appTitle')}</h1>
        <p>{t(locale, 'appSubtitle')}</p>
        <div className="row">
          <label htmlFor="locale-select">{t(locale, 'languageLabel')}</label>
          <select
            id="locale-select"
            value={locale}
            onChange={(event) => setLocale(event.target.value as Locale)}
          >
            <option value="en">EN</option>
            <option value="fr">FR</option>
          </select>
        </div>
      </header>

      {launchContext ? (
        <section className="panel" aria-live="polite">
          <h2>{t(locale, 'launchContextTitle')}</h2>
          <p>{t(locale, 'launchContextDescription')}</p>
          <pre className="context-box">{launchContext}</pre>
        </section>
      ) : null}

      <section className="panel">
        <h2>{t(locale, 'workflowLabel')}</h2>
        <div className="workflow-picker">
          <button
            className={workflow === 'u2' ? 'active' : ''}
            type="button"
            aria-pressed={workflow === 'u2'}
            onClick={() => setWorkflow('u2')}
          >
            {t(locale, 'workflowU2Title')}
          </button>
          <button
            className={workflow === 'u3' ? 'active' : ''}
            type="button"
            aria-pressed={workflow === 'u3'}
            onClick={() => setWorkflow('u3')}
          >
            {t(locale, 'workflowU3Title')}
          </button>
        </div>
        <p>{workflow === 'u2' ? t(locale, 'workflowU2Description') : t(locale, 'workflowU3Description')}</p>
      </section>

      <section className="layout">
        <form className="panel" onSubmit={onSubmit}>
          <h2>{t(locale, 'formTitle')}</h2>
          {workflow === 'u2' ? (
            <>
              <label htmlFor="u2-title">{t(locale, 'u2ModuleTitleLabel')}</label>
              <input
                id="u2-title"
                value={u2ModuleTitle}
                maxLength={200}
                onChange={(event) => setU2ModuleTitle(event.target.value)}
              />
              <label htmlFor="u2-topics">{t(locale, 'u2TopicsLabel')}</label>
              <textarea
                id="u2-topics"
                rows={5}
                maxLength={5000}
                value={u2Topics}
                onChange={(event) => setU2Topics(event.target.value)}
              />
            </>
          ) : (
            <>
              <label htmlFor="u3-reading">{t(locale, 'u3ReadingLabel')}</label>
              <textarea
                id="u3-reading"
                rows={5}
                maxLength={5000}
                value={u3Reading}
                onChange={(event) => setU3Reading(event.target.value)}
              />
              <label htmlFor="u3-bloom">{t(locale, 'u3BloomLabel')}</label>
              <select
                id="u3-bloom"
                value={u3Bloom}
                onChange={(event) => setU3Bloom(event.target.value as BloomLevel)}
              >
                <option value="remember">{t(locale, 'bloomRemember')}</option>
                <option value="understand">{t(locale, 'bloomUnderstand')}</option>
                <option value="apply">{t(locale, 'bloomApply')}</option>
                <option value="analyze">{t(locale, 'bloomAnalyze')}</option>
              </select>
              <label htmlFor="u3-count">{t(locale, 'u3CountLabel')}</label>
              <input
                id="u3-count"
                type="number"
                min={1}
                max={20}
                value={u3Count}
                onChange={(event) => setU3Count(Number(event.target.value || 1))}
              />
            </>
          )}
          <button type="submit">{t(locale, 'submitButton')}</button>
        </form>

        <section className="panel">
          <h2>{t(locale, 'previewTitle')}</h2>
          {preview ? (
            <result-preview
              title={preview.title}
              content={preview.content}
              metadata={preview.metadata}
            />
          ) : (
            <p>{t(locale, 'previewEmpty')}</p>
          )}
          <button type="button" disabled={!preview} onClick={() => setShowConfirmation(true)}>
            {t(locale, 'writeBackButton')}
          </button>
          {writeBackStatus ? <p className="status">{writeBackStatus}</p> : null}
        </section>
      </section>

      {showConfirmation ? (
        <div className="dialog-backdrop" role="presentation">
          <div className="dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
            <h2 id="confirm-title">{t(locale, 'confirmTitle')}</h2>
            <p>{t(locale, 'confirmBody')}</p>
            <div className="dialog-actions">
              <button
                type="button"
                onClick={() => {
                  setShowConfirmation(false)
                  setWriteBackStatus(t(locale, 'writeBackStatusCancelled'))
                }}
              >
                {t(locale, 'confirmCancel')}
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowConfirmation(false)
                  setWriteBackStatus(t(locale, 'writeBackStatusConfirmed'))
                }}
              >
                {t(locale, 'confirmApprove')}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </main>
  )
}

export default App
