<script>
  // Réglages : les réglages d'usage (recherche d'origine) et leur restauration depuis une sauvegarde de l'Anneau,
  // les livres (déposer, supprimer avec corbeille de 30 jours), les équivalences d'ingrédients,
  // le journal (avec Annuler), la version et la déconnexion.
  import { onMount } from 'svelte'
  import Upload from '@lucide/svelte/icons/upload'
  import Trash2 from '@lucide/svelte/icons/trash-2'
  import RotateCcw from '@lucide/svelte/icons/rotate-ccw'
  import X from '@lucide/svelte/icons/x'
  import History from '@lucide/svelte/icons/history'
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
  let dejaImporte = $state(null)    // livre déjà importé (et pas supprimé) qu'on vient de redéposer
  let eqA = $state('')
  let eqB = $state('')
  // Réglages d'usage (fichier reglages.json de l'appli ; repris une fois de la stack au premier démarrage)
  let reglages = $state(null)
  let messageReglages = $state('')
  let erreurReglages = $state('')
  // Restaurer : dates sauvegardées chez l'Anneau, date choisie, différences (actuel → sauvegardé)
  let dates = $state(null)
  let jour = $state('')
  let apercu = $state(null)
  let messageRestaurer = $state('')
  let erreurRestaurer = $state('')
  let restauration = $state(false)

  const noms = { import: 'Import', suppression: 'Suppression', restauration: 'Restauration', effacement: 'Effacement', correction: 'Correction',
                 rattachement: 'Ingrédient rattaché', ignore: 'Recette écartée', equivalence: 'Équivalence', annulation: 'Annulation',
                 reglage: 'Réglage', restauration_reglages: 'Réglages restaurés' }
  const date = (d) => new Date(d).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long' })
  const jourLong = (d) => new Date(`${d}T12:00:00`).toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
  const valeur = (v) => (v === true ? 'oui' : v === false ? 'non' : String(v ?? '—'))

  async function chargerReglages() {
    try { reglages = await api.get('/api/reglages') } catch (e) { erreurReglages = e.message }
  }
  async function changerReglage(cle, v) {
    messageReglages = erreurReglages = ''
    try {
      reglages = await api.put('/api/reglages', { [cle]: v })
      messageReglages = v ? 'Recherche d\'origine rallumée : la tâche de fond reprend les recettes sans origine.'
                          : 'Recherche d\'origine coupée : Comptoir ne demande plus rien à Wikidata.'
      journal = await api.get('/api/journal')
      apercu = null
    } catch (e) { erreurReglages = e.message; await chargerReglages() }
  }
  async function chercherDates() {
    messageRestaurer = erreurRestaurer = ''
    apercu = null
    try {
      dates = (await api.get('/api/restaurer')).dates
      jour = dates[0] ?? ''
      if (!dates.length) messageRestaurer = 'L\'Anneau n\'a encore aucune sauvegarde de Comptoir.'
    } catch (e) { dates = null; erreurRestaurer = e.message }
  }
  async function comparer() {
    messageRestaurer = erreurRestaurer = ''
    apercu = null
    try { apercu = await api.get(`/api/restaurer?le=${encodeURIComponent(jour)}`) } catch (e) { erreurRestaurer = e.message }
  }
  async function restaurerReglages() {
    restauration = true
    erreurRestaurer = ''
    try {
      const r = await api.post('/api/restaurer', { le: jour })
      reglages = r.reglages
      messageRestaurer = r.changes ? `Réglages du ${jourLong(jour)} restaurés.` : 'Rien à changer : les réglages sont déjà ceux de cette sauvegarde.'
      apercu = null
      journal = await api.get('/api/journal')
      recharger()
    } catch (e) { erreurRestaurer = e.message } finally { restauration = false }
  }

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
    dejaImporte = null
    try {
      const r = await api.envoyer(`/api/livres/import?nom=${encodeURIComponent(fichier.name)}`, fichier)
      message = `« ${r.titre} » : ${r.recettes} recettes lues${r.a_verifier ? `, dont ${r.a_verifier} à vérifier dans À traiter` : ''}`
        + `${r.conseils ? `, et ${r.conseils} conseil${r.conseils > 1 ? 's' : ''} rangé${r.conseils > 1 ? 's' : ''} dans Cocktails › Conseils` : ''}.`
        + (r.a_reperes_page ? '' : ' Ce livre ne porte pas les pages du livre papier : aucune page ne sera affichée.')
      await Promise.all([charger(), recharger()])
    } catch (err) {
      if (err.donnees?.corbeille) aRestaurer = corbeille.find((c) => c.id === err.donnees.corbeille) ?? { id: err.donnees.corbeille }
      if (err.donnees?.deja) dejaImporte = livres.find((l) => l.id === err.donnees.deja) ?? { id: err.donnees.deja }
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
    // Efface l'ancienne lecture, puis relit le même fichier avec le découpage de cette version.
    // Livre encore actif : il passe d'abord par la corbeille (la suppression est notée au journal).
    const id = (aRestaurer ?? dejaImporte).id
    if (dejaImporte) await api.del(`/api/livres/${id}`)
    await api.del(`/api/corbeille/${id}`)
    aRestaurer = dejaImporte = null
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
  onMount(async () => { await Promise.all([charger(), chargerReglages()]); ingredients = await api.get('/api/ingredients') })
  const bloc = 'max-w-3xl rounded-2xl border bg-card p-5'
</script>

<h1 class="titre mb-6">Réglages</h1>

<div class="grid gap-4">
  <section class={bloc} aria-labelledby="titre-reglages">
    <h2 id="titre-reglages" class="text-lg font-semibold">Réglages</h2>
    {#if reglages}
      <div class="mt-3 flex items-start justify-between gap-4">
        <span class="min-w-0">
          <span id="libelle-recherche" class="block font-medium">Recherche d'origine dans Wikidata</span>
          <span class="text-sm text-muted-foreground">Cherche le pays ou le lieu de création des cocktails, une fois par recette, en lecture seule.</span>
        </span>
        <button type="button" role="switch" aria-checked={reglages.recherche_web} aria-labelledby="libelle-recherche"
                onclick={() => changerReglage('recherche_web', !reglages.recherche_web)}
                class="relative mt-1 inline-flex h-7 w-12 shrink-0 items-center rounded-full border transition-colors aria-checked:border-transparent aria-checked:bg-primary bg-secondary">
          <span class={`inline-block size-5 rounded-full shadow transition-transform ${reglages.recherche_web ? 'translate-x-6 bg-primary-foreground' : 'translate-x-1 bg-foreground'}`}></span>
        </button>
      </div>
    {/if}
    {#if messageReglages}<p class="mt-3 text-sm" role="status">{messageReglages}</p>{/if}
    {#if erreurReglages}<p class="mt-3 text-sm text-destructive" role="alert">{erreurReglages}</p>{/if}
    <p class="mt-3 text-sm text-muted-foreground">La clé Mistral reste dans la stack (COMPTOIR_MISTRAL_CLE) : un secret ne se règle pas ici et ne part dans aucune sauvegarde.</p>
  </section>

  <section class={bloc} aria-labelledby="titre-restaurer">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h2 id="titre-restaurer" class="text-lg font-semibold">Restaurer les réglages</h2>
      <Button variant="outline" onclick={chercherDates}><History class="size-4" /> Voir les sauvegardes</Button>
    </div>
    <p class="mt-1 text-sm text-muted-foreground">L'Anneau garde chaque nuit une copie des réglages ci-dessus. Restaurer ne touche ni aux livres, ni au bar, ni aux favoris.</p>
    {#if dates?.length}
      <div class="mt-3 flex flex-wrap items-center gap-2">
        <select bind:value={jour} aria-label="Date de la sauvegarde" onchange={() => (apercu = null)} class="h-10 min-w-0 max-w-full rounded-lg border border-input bg-card px-2">
          {#each dates as d}<option value={d}>{jourLong(d)}</option>{/each}
        </select>
        <Button variant="outline" onclick={comparer}>Comparer</Button>
      </div>
    {/if}
    {#if apercu}
      {#if !apercu.differences.length}
        <p class="mt-3 text-sm" role="status">Rien ne diffère : les réglages actuels sont ceux de cette sauvegarde.</p>
      {:else}
        <ul aria-label="Différences avec la sauvegarde" class="mt-3 divide-y text-sm">
          {#each apercu.differences as d (d.cle)}
            <li class="flex flex-wrap justify-between gap-x-4 gap-y-1 py-2">
              <span class="min-w-0 font-medium">{d.nom}</span>
              <span class="tabular-nums"><span class="text-muted-foreground">{valeur(d.actuel)}</span> → {valeur(d.sauve)}</span>
            </li>
          {/each}
        </ul>
        <div class="mt-3 flex flex-wrap gap-2">
          <Button onclick={restaurerReglages} disabled={restauration}><RotateCcw class="size-4" /> Restaurer ces réglages</Button>
          <Button variant="ghost" onclick={() => (apercu = null)}>Garder les actuels</Button>
        </div>
      {/if}
    {/if}
    {#if messageRestaurer}<p class="mt-3 text-sm" role="status">{messageRestaurer}</p>{/if}
    {#if erreurRestaurer}<p class="mt-3 text-sm text-destructive" role="alert">{erreurRestaurer}</p>{/if}
  </section>

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
    {#if dejaImporte}
      <Button class="mt-2" variant="outline" onclick={reimporterANeuf} disabled={envoi}><Upload class="size-4" /> Réimporter à neuf</Button>
      <p class="mt-2 text-sm text-muted-foreground">Relit le livre avec le découpage de cette version. L'ancienne lecture est effacée, avec ses favoris et ses corrections ; ton bar ne change pas.</p>
    {/if}
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
