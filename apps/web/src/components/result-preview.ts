import { LitElement, css, html } from 'lit'

export class ResultPreview extends LitElement {
  static properties = {
    title: { type: String },
    content: { type: String },
    metadata: { type: String },
  }

  title = ''
  content = ''
  metadata = ''

  static styles = css`
    :host {
      display: block;
      border: 1px solid #d6dde8;
      border-radius: 8px;
      background: #ffffff;
      padding: 1rem;
      min-height: 13rem;
      color: #1d2f57;
    }

    h3 {
      margin: 0 0 0.75rem;
      font-size: 1rem;
      color: #1d2f57;
    }

    pre {
      margin: 0;
      white-space: pre-wrap;
      font-family: Inter, 'Segoe UI', sans-serif;
      line-height: 1.5;
      color: #243b69;
    }

    p {
      margin: 0.75rem 0 0;
      color: #4668ad;
      font-size: 0.85rem;
    }
  `

  render() {
    return html`
      <h3>${this.title}</h3>
      <pre>${this.content}</pre>
      ${this.metadata ? html`<p>${this.metadata}</p>` : null}
    `
  }
}

if (!customElements.get('result-preview')) {
  customElements.define('result-preview', ResultPreview)
}
