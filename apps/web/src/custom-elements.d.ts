import type * as React from 'react'
import type { ResultPreview } from './components/result-preview'

declare module 'react' {
  namespace JSX {
    interface IntrinsicElements {
      'result-preview': React.DetailedHTMLProps<
        React.HTMLAttributes<ResultPreview>,
        ResultPreview
      > & {
        title?: string
        content?: string
        metadata?: string
      }
    }
  }
}

export {}
