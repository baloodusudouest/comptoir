<script>
  // Corriger une recette : titre, ingrédients (un par ligne), préparation (une étape par ligne), chapeau.
  // « Relire par Mistral » (si une clé est réglée) remplit le formulaire avec sa proposition ; rien n'est
  // enregistré avant « Enregistrer ». L'original du livre reste visible à côté.
  import Sparkles from '@lucide/svelte/icons/sparkles'
  import { api } from '$lib/api.js'
  import { Button } from '$lib/components/ui/button/index.js'

  let { recette, mistral = false, onfini, onannuler } = $props()

  let titre = $state(recette.titre)
  let lignes = $state(recette.lignes.map((l) => l.texte).join('\n'))
  let etapes = $state(recette.etapes.join('\n'))
  let chapeau = $state(recette.chapeau)
  let source = $state('main')
  let erreur = $state('')
  let attente = $state('')

  async function relire() {
    attente = 'mistral'
    erreur = ''
    try {
      const p = await api.post(`/api/recettes/${recette.id}/mistral`)
      if (!p.lignes.length) { erreur = "Mistral ne voit pas de recette dans ce texte."; return }
      titre = p.titre || titre
      lignes = p.lignes.join('\n')
      etapes = p.etapes.join('\n')
      chapeau = p.chapeau || chapeau
      source = 'mistral'
    } catch (e) {
      erreur = e.message
    } finally {
      attente = ''
    }
  }

  async function enregistrer(e) {
    e.preventDefault()
    attente = 'enregistrer'
    erreur = ''
    try {
      const r = await api.put(`/api/recettes/${recette.id}`, {
        titre, chapeau, source,
        lignes: lignes.split('\n').map((x) => x.trim()).filter(Boolean),
        etapes: etapes.split('\n').map((x) => x.trim()).filter(Boolean),
      })
      onfini?.(r)
    } catch (err) {
      erreur = err.message
    } finally {
      attente = ''
    }
  }
  const champ = 'w-full rounded-lg border border-input bg-transparent px-3 py-2 outline-none focus:border-ring'
</script>

<div class="grid gap-6 lg:grid-cols-2">
  <section aria-labelledby="titre-original" class="min-w-0 rounded-2xl border bg-card p-5">
    <h2 id="titre-original" class="text-sm font-medium text-muted-foreground">Texte lu dans le livre</h2>
    <pre class="mt-3 font-sans text-sm whitespace-pre-wrap text-muted-foreground">{recette.texte_original}</pre>
  </section>
  <form class="flex min-w-0 flex-col gap-4" onsubmit={enregistrer}>
    <label class="flex flex-col gap-1.5 text-sm">Nom
      <input class={champ} bind:value={titre} required />
    </label>
    <label class="flex flex-col gap-1.5 text-sm">Ingrédients, un par ligne
      <textarea class={champ} rows="7" bind:value={lignes} required></textarea>
    </label>
    <label class="flex flex-col gap-1.5 text-sm">Préparation, une étape par ligne
      <textarea class={champ} rows="5" bind:value={etapes}></textarea>
    </label>
    <label class="flex flex-col gap-1.5 text-sm">Présentation (facultatif)
      <textarea class={champ} rows="2" bind:value={chapeau}></textarea>
    </label>
    {#if source === 'mistral'}<p class="text-sm text-primary" role="status">Proposition de Mistral : relis-la avant d'enregistrer.</p>{/if}
    {#if erreur}<p class="text-sm text-destructive" role="alert">{erreur}</p>{/if}
    <div class="flex flex-wrap gap-2">
      <Button type="submit" disabled={!!attente}>{attente === 'enregistrer' ? 'Enregistrement…' : 'Enregistrer'}</Button>
      {#if mistral}
        <Button type="button" variant="outline" onclick={relire} disabled={!!attente}>
          <Sparkles class="size-4" aria-hidden="true" /> {attente === 'mistral' ? 'Mistral relit…' : 'Relire par Mistral'}
        </Button>
      {/if}
      <Button type="button" variant="ghost" onclick={onannuler}>Annuler</Button>
    </div>
  </form>
</div>
