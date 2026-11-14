<script>
  // Réglages : les livres (déposer, supprimer avec corbeille de 30 jours),
  // les équivalences d'ingrédients, le journal (avec Annuler), la version et la déconnexion.
  import { onMount } from 'svelte'
  import Upload from '@lucide/svelte/icons/upload'
  import Trash2 from '@lucide/svelte/icons/trash-2'
  import RotateCcw from '@lucide/svelte/icons/rotate-ccw'
  import X from '@lucide/svelte/icons/x'
  import { api } from '$lib/api.js'
  import { recharger } from '$lib/donnees.svelte.js'
  import { Button } from '$lib/components/ui/button/index.js'

  let { session, deconnecter } = $props()
  let livres = $state([])
  let corbeille = $state([])
  let journal = $state([])
  let equivalences = $state([])
  let ingredients = $state([])
  let message = $state('')
  let erreur = $state('')
  let envoi = $state(false)
  let aSupprimer = $state(null)     // aperçu de la suppression en attente de confirmation
  let aRestaurer = $state(null)     // livre en corbeille proposé à la place d'un nouvel import
  let dernierFichier = null        // le fichier déposé, pour « Réimporter à neuf »
  let eqA = $state('')
  let eqB = $state('')

  const noms = { import: 'Import', suppression: 'Suppression', restauration: 'Restauration', effacement: 'Effacement', correction: 'Correction',
                 rattachement: 'Ingrédient rattaché', ignore: 'Recette écartée', equivalence: 'Équivalence', annulation: 'Annulation' }
  const date = (d) => new Date(d).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long' })

  async function charger() {
    ;[livres, corbeille, journal, equivalences] = await Promise.all(
      ['/api/livres', '/api/corbeille', '/api/journal', '/api/equivalences'].map((c) => api.get(c)))
  }
  async function deposer(e) {
    const fichier = e.currentTarget.files?.[0]
    e.currentTarget.value = ''
    if (!fichier) return
    await importer(fichier)
  }
  async function importer(fichier) {
    dernierFichier = fichier
    envoi = true
    message = erreur = ''
    aRestaurer = null
    try {
      const r = await api.envoyer(`/api/livres/import?nom=${encodeURIComponent(fichier.name)}`, fichier)
      message = `« ${r.titre} » : ${r.recettes} recettes lues${r.a_verifier ? `, dont ${r.a_verifier} à vérifier dans À traiter` : ''}`
        + `${r.conseils ? `, et ${r.conseils} conseil${r.conseils > 1 ? 's' : ''} rangé${r.conseils > 1 ? 's' : ''} dans Cocktails › Conseils` : ''}.`
        + (r.a_reperes_page ? '' : ' Ce livre ne porte pas les pages du livre papier : aucune page ne sera affichée.')
      await Promise.all([charger(), recharger()])
    } catch (err) {
      if (err.donnees?.corbeille) aRestaurer = corbeille.find((c) => c.id === err.donnees.corbeille) ?? { id: err.donnees.corbeille }
      erreur = err.message
    } finally {
      envoi = false
    }
  }
  async function demanderSuppression(l) {
    aSupprimer = { id: l.id, ...(await api.get(`/api/livres/${l.id}/suppression`)) }
  }
  async function supprimer() {
    await api.del(`/api/livres/${aSupprimer.id}`)
    message = `« ${aSupprimer.titre} » est dans la corbeille pour ${aSupprimer.jours} jours.`
    aSupprimer = null
    await Promise.all([charger(), recharger()])
  }
  async function effacer(c) {
    await api.del(`/api/corbeille/${c.id}`)
    message = `« ${c.titre ?? 'Le livre'} » est effacé pour de bon. Tu peux le déposer à nouveau.`
    await charger()
  }
  async function reimporterANeuf() {
    // Efface l'ancienne lecture (corbeille), puis relit le même fichier avec le découpage de cette version
    await api.del(`/api/corbeille/${aRestaurer.id}`)
    aRestaurer = null
    await importer(dernierFichier)
  }
  async function restaurer(id) {
    await api.post(`/api/livres/${id}/restaurer`)
    aRestaurer = null
    erreur = ''
    message = 'Livre restauré, avec ses favoris et ses corrections.'
    await Promise.all([charger(), recharger()])
  }
  async function annuler(j) {
    try {
      await api.post(`/api/journal/${j.id}/annuler`)
      await Promise.all([charger(), recharger()])
    } catch (e) { erreur = e.message }
  }
  async function ajouterEquivalence() {
    const a = ingredients.find((i) => i.chemin.join(' › ') === eqA), b = ingredients.find((i) => i.chemin.join(' › ') === eqB)
    if (!a || !b) { erreur = 'Choisir deux ingrédients dans la liste.'; return }
    equivalences = await api.post('/api/equivalences', { a: a.id, b: b.id })
    eqA = eqB = ''
    recharger()
  }
  async function retirerEquivalence(e) {
    equivalences = await api.del(`/api/equivalences/${e.a}/${e.b}`)
    recharger()
  }
  onMount(async () => { await charger(); ingredients = await api.get('/api/ingredients') })
  const bloc = 'max-w-3xl rounded-2xl border bg-card p-5'
</script>

<h1 class="titre mb-6">Réglages</h1>

<div class="grid gap-4">
  <section class={bloc} aria-labelledby="titre-livres">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h2 id="titre-livres" class="text-lg font-semibold">Livres</h2>
      <label class="inline-flex h-10 cursor-pointer items-center gap-2 rounded-lg bg-primary px-4 text-sm font-medium text-primary-foreground has-[:disabled]:opacity-60">
        <Upload class="size-4" aria-hidden="true" /> {envoi ? 'Lecture du livre…' : 'Déposer un EPUB'}
        <input type="file" accept=".epub,application/epub+zip" class="sr-only" onchange={deposer} disabled={envoi} />
      </label>
    </div>
    {#if message}<p class="mt-3 text-sm" role="status">{message}</p>{/if}
    {#if erreur}<p class="mt-3 text-sm text-destructive" role="alert">{erreur}</p>{/if}
    {#if aRestaurer}
      <div class="mt-2 flex flex-wrap gap-2">
        <Button variant="outline" onclick={() => restaurer(aRestaurer.id)}><RotateCcw class="size-4" /> Restaurer tel quel</Button>
        <Button variant="outline" onclick={reimporterANeuf}><Upload class="size-4" /> Réimporter à neuf</Button>
      </div>
      <p class="mt-2 text-sm text-muted-foreground">« Réimporter à neuf » relit le livre avec le découpage de cette version ; ses favoris et corrections sont perdus.</p>
    {/if}
    {#if !livres.length}
      <p class="mt-3 text-sm text-muted-foreground">Aucun livre. Les EPUB fabriqués par Scriptorium portent les pages du livre papier ; un EPUB protégé par DRM ne peut pas être lu.</p>
    {:else}
      <ul aria-label="Livres importés" class="mt-3 divide-y">
        {#each livres as l (l.id)}
          <li class="flex items-center justify-between gap-3 py-3">
            <span class="min-w-0">
              <span class="block font-medium">{l.titre}</span>
              <span class="text-sm text-muted-foreground">{l.recettes} recettes{l.a_verifier ? `, ${l.a_verifier} à vérifier` : ''}{l.a_reperes_page ? '' : ', sans pages du livre papier'}</span>
            </span>
            <Button variant="ghost" size="sm" onclick={() => demanderSuppression(l)} aria-label={`Supprimer ${l.titre}`}><Trash2 class="size-4" /> Supprimer</Button>
          </li>
        {/each}
      </ul>
    {/if}
    {#if aSupprimer}
      <div class="mt-3 rounded-xl border border-destructive/60 p-4" role="alertdialog" aria-labelledby="titre-confirmer">
        <p id="titre-confirmer" class="font-medium">Supprimer « {aSupprimer.titre} » ?</p>
        <p class="mt-1 text-sm text-muted-foreground">
          {aSupprimer.recettes} cocktails disparaissent de partout{aSupprimer.favoris ? `, dont ${aSupprimer.favoris} favori${aSupprimer.favoris > 1 ? 's' : ''}` : ''}{aSupprimer.corrections ? ` et ${aSupprimer.corrections} correction${aSupprimer.corrections > 1 ? 's' : ''}` : ''}.
          Ton bar ne change pas. Le livre reste {aSupprimer.jours} jours dans la corbeille, restaurable tel quel.
        </p>
        <div class="mt-3 flex gap-2">
          <Button variant="destructive" onclick={supprimer}>Supprimer le livre et ses cocktails</Button>
          <Button variant="ghost" onclick={() => (aSupprimer = null)}>Garder</Button>
        </div>
      </div>
    {/if}
  </section>

  {#if corbeille.length}
    <section class={bloc} aria-labelledby="titre-corbeille">
      <h2 id="titre-corbeille" class="text-lg font-semibold">Corbeille</h2>
      <ul class="mt-2 divide-y">
        {#each corbeille as c (c.id)}
          <li class="flex items-center justify-between gap-3 py-3">
            <span class="min-w-0"><span class="block font-medium">{c.titre}</span>
              <span class="text-sm text-muted-foreground">{c.recettes} recettes, effacé pour de bon le {date(c.efface_le)}</span></span>
            <span class="flex shrink-0 gap-1">
              <Button variant="outline" size="sm" onclick={() => restaurer(c.id)}><RotateCcw class="size-4" /> Restaurer</Button>
              <Button variant="ghost" size="sm" onclick={() => effacer(c)} aria-label={`Effacer ${c.titre} maintenant`}><X class="size-4" /> Effacer maintenant</Button>
            </span>
          </li>
        {/each}
      </ul>
    </section>
  {/if}

  <section class={bloc} aria-labelledby="titre-equivalences">
    <h2 id="titre-equivalences" class="text-lg font-semibold">Équivalences d'ingrédients</h2>
    <p class="mt-1 text-sm text-muted-foreground">Deux ingrédients qui se remplacent l'un l'autre chez toi, dans les deux sens (par exemple, sirop de sucre et sirop d'agave).</p>
    {#if equivalences.length}
      <ul class="mt-2 divide-y">
        {#each equivalences as e}
          <li class="flex items-center justify-between gap-3 py-2"><span>{e.nom_a} = {e.nom_b}</span>
            <Button variant="ghost" size="sm" aria-label={`Retirer ${e.nom_a} = ${e.nom_b}`} onclick={() => retirerEquivalence(e)}><X class="size-4" /></Button></li>
        {/each}
      </ul>
    {/if}
    <div class="mt-3 flex flex-wrap items-center gap-2">
      <input list="liste-ingredients" bind:value={eqA} placeholder="Ingrédient" aria-label="Premier ingrédient" class="h-10 w-56 rounded-lg border border-input bg-transparent px-3" />
      <span>=</span>
      <input list="liste-ingredients" bind:value={eqB} placeholder="Ingrédient" aria-label="Second ingrédient" class="h-10 w-56 rounded-lg border border-input bg-transparent px-3" />
      <Button variant="outline" onclick={ajouterEquivalence}>Ajouter</Button>
    </div>
    <datalist id="liste-ingredients">{#each ingredients.filter((i) => i.niveau !== 'categorie') as i}<option value={i.chemin.join(' › ')}></option>{/each}</datalist>
  </section>

  <section class={bloc} aria-labelledby="titre-journal">
    <h2 id="titre-journal" class="text-lg font-semibold">Journal</h2>
    {#if !journal.length}
      <p class="mt-1 text-sm text-muted-foreground">Rien encore : le journal note chaque import, suppression, correction et rattachement.</p>
    {:else}
      <ul class="mt-2 divide-y text-sm">
        {#each journal as j (j.id)}
          <li class="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 py-2">
            <span class="min-w-0"><span class="font-medium">{noms[j.action] ?? j.action}</span> : {j.cible}{#if j.detail}{' '}<span class="text-muted-foreground">({j.detail})</span>{/if}</span>
            <span class="flex items-center gap-2">
              {#if j.annulable && !j.annule && ['correction', 'rattachement', 'ignore'].includes(j.action)}
                <Button variant="ghost" size="sm" onclick={() => annuler(j)}>Annuler</Button>
              {:else if j.annule}<span class="text-muted-foreground">annulé</span>{/if}
              <time class="text-muted-foreground tabular-nums" datetime={j.le}>{new Date(j.le).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })}</time>
            </span>
          </li>
        {/each}
      </ul>
    {/if}
  </section>
</div>

<p class="mt-6 flex max-w-3xl items-center justify-between gap-3 text-sm text-muted-foreground">
  <span>Comptoir {session.version}</span>
  <Button variant="outline" onclick={deconnecter}>Se déconnecter</Button>
</p>
