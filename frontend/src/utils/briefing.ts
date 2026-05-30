import type { ParsedBriefing } from '../api/types'

function findMetric(lines: string[], prefix: string): string {
  const line = lines.find((entry) => entry.startsWith(prefix))
  return line ? line.slice(prefix.length).trim() : 'n/a'
}

function extractSection(lines: string[], heading: string): string[] {
  const startIndex = lines.findIndex((line) => line.trim() === heading)
  if (startIndex < 0) {
    return []
  }

  const sectionLines: string[] = []
  for (let index = startIndex + 1; index < lines.length; index += 1) {
    const line = lines[index].trim()
    if (!line) {
      if (sectionLines.length > 0) {
        break
      }
      continue
    }

    if (!line.startsWith('- ')) {
      if (sectionLines.length > 0) {
        break
      }
      continue
    }

    sectionLines.push(line.replace(/^-\s*/, '').trim())
  }

  return sectionLines
}

export function parseBriefing(text: string): ParsedBriefing {
  const lines = text
    .split(/\r?\n/)
    .map((line) => line.trim())

  const title = lines.find((line) => line.toLowerCase().includes('daily executive briefing')) ?? 'OpsPilot Daily Briefing'

  return {
    title,
    metrics: {
      totalWorkItems: findMetric(lines, 'Total Work Items:'),
      urgencyMix: findMetric(lines, 'Urgency Mix:'),
      sentimentMix: findMetric(lines, 'Sentiment Mix:'),
    },
    topPriorities: extractSection(lines, 'Top Priorities:'),
    dueSoon: extractSection(lines, 'Due-Soon Action Items:'),
    rawText: text,
  }
}
