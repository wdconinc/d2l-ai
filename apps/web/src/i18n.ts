export type Locale = 'en' | 'fr'

const translations = {
  en: {
    appTitle: 'UM AI Assistant',
    appSubtitle: 'LTI launch workspace for Brightspace workflows.',
    languageLabel: 'Language',
    workflowLabel: 'Workflow',
    workflowU2Title: 'U2 Module summary',
    workflowU2Description: 'Create a draft summary for selected module topics.',
    workflowU3Title: 'U3 Quiz generation',
    workflowU3Description: 'Create draft question bank items with Bloom targeting.',
    launchContextTitle: 'Launch context (development)',
    launchContextDescription: 'Sanitized launch values for local development only.',
    formTitle: 'Workflow input',
    u2ModuleTitleLabel: 'Module title',
    u2TopicsLabel: 'Source topics (one per line)',
    u3ReadingLabel: 'Reading excerpt',
    u3BloomLabel: 'Bloom level',
    u3CountLabel: 'Question count',
    submitButton: 'Preview draft',
    previewTitle: 'Result preview',
    previewEmpty: 'Submit workflow input to see a generated draft preview.',
    writeBackButton: 'Write back to Brightspace',
    confirmTitle: 'Confirm Brightspace write-back',
    confirmBody:
      'This action sends the reviewed draft to Brightspace. Continue only after instructor review.',
    confirmCancel: 'Cancel',
    confirmApprove: 'Confirm write-back',
    writeBackStatusConfirmed: 'Write-back confirmed. Submit request to backend API.',
    writeBackStatusCancelled: 'Write-back cancelled. Draft remains local.',
    previewMetadataU2: 'mode=draft | workflow=u2',
    previewMetadataU3: 'mode=draft | workflow=u3',
    previewEmptyValue: '—',
    bloomRemember: 'Remember',
    bloomUnderstand: 'Understand',
    bloomApply: 'Apply',
    bloomAnalyze: 'Analyze',
  },
  fr: {
    appTitle: 'Assistant IA UM',
    appSubtitle: 'Espace de lancement LTI pour les flux Brightspace.',
    languageLabel: 'Langue',
    workflowLabel: 'Flux',
    workflowU2Title: 'U2 Résumé de module',
    workflowU2Description:
      'Créer un brouillon de résumé pour les sujets de module sélectionnés.',
    workflowU3Title: 'U3 Génération de quiz',
    workflowU3Description:
      'Créer des brouillons de questions avec ciblage du niveau de Bloom.',
    launchContextTitle: 'Contexte de lancement (développement)',
    launchContextDescription:
      'Valeurs de lancement assainies pour le développement local seulement.',
    formTitle: 'Entrée du flux',
    u2ModuleTitleLabel: 'Titre du module',
    u2TopicsLabel: 'Sujets source (un par ligne)',
    u3ReadingLabel: 'Extrait de lecture',
    u3BloomLabel: 'Niveau de Bloom',
    u3CountLabel: 'Nombre de questions',
    submitButton: 'Aperçu du brouillon',
    previewTitle: 'Aperçu du résultat',
    previewEmpty: 'Soumettez les entrées du flux pour afficher un aperçu généré.',
    writeBackButton: 'Écrire vers Brightspace',
    confirmTitle: 'Confirmer l’écriture vers Brightspace',
    confirmBody:
      'Cette action envoie le brouillon révisé vers Brightspace. Continuez seulement après la révision de l’instructeur.',
    confirmCancel: 'Annuler',
    confirmApprove: 'Confirmer l’écriture',
    writeBackStatusConfirmed:
      'Écriture confirmée. Envoyer la requête à l’API backend.',
    writeBackStatusCancelled: 'Écriture annulée. Le brouillon reste local.',
    previewMetadataU2: 'mode=brouillon | flux=u2',
    previewMetadataU3: 'mode=brouillon | flux=u3',
    previewEmptyValue: '—',
    bloomRemember: 'Mémoriser',
    bloomUnderstand: 'Comprendre',
    bloomApply: 'Appliquer',
    bloomAnalyze: 'Analyser',
  },
} as const

type TranslationKey = keyof (typeof translations)['en']

export const t = (locale: Locale, key: TranslationKey): string => translations[locale][key]
