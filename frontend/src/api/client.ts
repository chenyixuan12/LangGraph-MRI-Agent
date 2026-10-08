export type Study = { id: string; filename: string; size_bytes: number; status: string; created_at: string }
export type Job = { id: string; study_id: string; status: string; scale: number; method: string; output_path?: string; error?: string }

export async function uploadStudy(file: File): Promise<Study> {
  const body = new FormData(); body.append('file', file)
  const response = await fetch('/api/v1/studies', { method: 'POST', body })
  if (!response.ok) throw new Error(await response.text())
  return response.json()
}

export async function createSuperResolution(studyId: string): Promise<Job> {
  const response = await fetch(`/api/v1/studies/${studyId}/super-resolution`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ scale: 2, method: 'baseline' }) })
  if (!response.ok) throw new Error(await response.text())
  return response.json()
}
