<script>
  // Fiche d'un cocktail : le livre et la page du livre papier pour le retrouver sur l'étagère,
  // la note du livre, les lieux, les ingrédients (ce qui manque en orange) recalculés pour N verres ou N litres, la préparation,
  // le verre et la déco, puis ce que le livre en dit (avis, origine, variante, autre nom).
  import { onMount } from 'svelte'
  import ArrowLeft from '@lucide/svelte/icons/arrow-left'
  import Star from '@lucide/svelte/icons/star'
  import Martini from '@lucide/svelte/icons/martini'
  import { api } from '$lib/api.js'
  import { recharger, dose } from '$lib/donnees.svelte.js'
  import Portions from '$lib/components/Portions.svelte'
  import { Button } from '$lib/components/ui/button/index.js'
  import Vignette from '$lib/components/Vignette.svelte'
  import Editeur from '$lib/components/Editeur.svelte'

  let { id, session } = $props()
  let r = $state(null)
  let erreur = $state('')
  let facteur = $state(1)                      // 2 verres → 2 ; 1,5 l d'un verre de 12 cl → 12,5
  let reglage = $state({ mode: 'verres', verres: 1, litres: 1 })
  let lienPreparer = $derived(reglage.mode === 'litres' ? `litres=${reglage.litres}` : `verres=${reglage.verres}`)
  // Rubriques du livre : le service (verre, déco) près de la préparation, le reste (avis, origine, variante…) en dessous
  const SERVICE = ['Verre', 'Déco']
  let service = $derived((r?.infos ?? []).filter((i) => SERVICE.includes(i.nom)))
  let livre = $derived((r?.infos ?? []).filter((i) => !SERVICE.includes(i.nom)))
  let edition = $state(false)

  const sources = { livre: 'd\'après le livre', wikidata: 'd\'après Wikidata', regle: 'd\'après le nom', main: 'choisi à la main' }

  async function charger() {
    try { r = await api.get(`/api/recettes/${id}`) } catch (e) { erreur = e.message }
  }
  async function basculerFavori() {
    const f = await api.post(`/api/recettes/${id}/favori`, { favori: !r.favori })
    r.favori = f.favori
    recharger()
  }
  async function ignorer() {
    await api.post(`/api/recettes/${id}/ignorer`)
    await recharger()
    location.hash = '#/cocktails'
  }
  onMount(charger)
</script>

<a href="#/cocktails" onclick={(e) => { if (history.length > 1) { e.preventDefault(); history.back() } }}
   class="mb-5 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground">
  <ArrowLeft class="size-4" aria-hidden="true" /> Retour
</a>

{#if erreur}
  <p class="text-destructive" role="alert">{erreur}</p>
{:else if r && edition}
  <h1 class="titre mb-6">Corriger la recette</h1>
  <Editeur recette={r} mistral={session.mistral} onannuler={() => (edition = false)}
           onfini={(n) => { r = n; edition = false; recharger() }} />
{:else if r}
  <article class="grid gap-8 md:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] md:gap-12">
    <div class="min-w-0">
      <Vignette recette={r} taille="lg" />
    </div>
    <div class="min-w-0">
      <div class="flex items-start justify-between gap-4">
        <h1 class="carte-nom text-3xl md:text-4xl">{r.titre}</h1>
        <button type="button" onclick={basculerFavori} aria-pressed={r.favori} aria-label={r.favori ? 'Retirer des favoris' : 'Ajouter aux favoris'}
                class="grid size-11 shrink-0 place-items-center rounded-full border hover:border-primary">
          <Star class={`size-5 ${r.favori ? 'fill-primary text-primary' : ''}`} aria-hidden="true" />
        </button>
      </div>
      <p class="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1 text-muted-foreground">
        <span>{r.livre}{#if r.pages}, <span class="text-foreground">{r.pages}</span>{/if}</span>
        {#if r.note}
          <span class="tracking-[0.15em] text-primary" role="img" aria-label={`Note du livre : ${r.note} sur 5`}>{'★'.repeat(r.note)}<span class="text-muted-foreground/40">{'★'.repeat(Math.max(0, 5 - r.note))}</span></span>
        {/if}
      </p>
      {#if r.etat === 'a_verifier'}
        <p class="mt-3 rounded-xl border border-primary/50 px-4 py-2 text-sm" role="status">Découpage à vérifier : compare avec le livre, puis corrige ou valide dans « À traiter ».</p>
      {/if}

      {#if r.lieux.length}
        <dl class="mt-5 grid gap-1.5 text-sm">
          {#each r.lieux as l}
            <div class="flex flex-wrap gap-x-2">
              <dt class="text-muted-foreground">{l.sorte === 'cree_a' ? 'Créé à' : 'Évoque'}</dt>
              <dd><a class="underline-offset-4 hover:underline" href="#/cocktails/lieux">{l.chemin.slice().reverse().join(', ')}</a>
                <span class="text-muted-foreground">({sources[l.source] ?? l.source})</span></dd>
            </div>
          {/each}
        </dl>
      {/if}

      {#if r.chapeau}<p class="mt-5 max-w-prose">{r.chapeau}</p>{/if}

      <section aria-labelledby="titre-ingredients" class="mt-8">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <h2 id="titre-ingredients" class="text-lg font-medium">Ingrédients</h2>
          <Portions lignes={r.lignes} bind:facteur bind:reglage />
        </div>
        <ul class="mt-3 divide-y">
          {#each r.lignes as l}
            <li class="flex items-baseline gap-3 py-2.5">
              <span class="w-24 shrink-0 text-right tabular-nums text-muted-foreground">{dose(l, facteur)}</span>
              <span class={l.present || l.facultatif ? '' : 'text-primary'}>
                {l.nom || l.texte}
                {#if l.facultatif}<span class="text-sm text-muted-foreground"> (facultatif)</span>{/if}
                {#if !l.present && !l.facultatif}<span class="sr-only"> (manque)</span>{/if}
              </span>
            </li>
          {/each}
        </ul>
        {#if r.manque}<p class="mt-2 text-sm text-primary">{r.manque > 1 ? `Il manque ${r.manque} ingrédients.` : 'Il manque un ingrédient.'}</p>{/if}
      </section>

      {#if r.etapes.length}
        <section aria-labelledby="titre-preparation" class="mt-8">
          <h2 id="titre-preparation" class="text-lg font-medium">Préparation</h2>
          <ol class="mt-3 grid list-decimal gap-2 pl-5 marker:text-muted-foreground">
            {#each r.etapes as e}<li class="max-w-prose pl-1">{e}</li>{/each}
          </ol>
        </section>
      {/if}

      {#if service.length}
        <dl class="mt-6 grid gap-x-4 gap-y-1.5 text-sm sm:grid-cols-[6rem_1fr]">
          {#each service as i}<dt class="text-muted-foreground">{i.nom}</dt><dd class="first-letter:uppercase">{i.texte}</dd>{/each}
        </dl>
      {/if}

      {#if livre.length}
        <section aria-labelledby="titre-livre" class="mt-8">
          <h2 id="titre-livre" class="text-lg font-medium">Dans le livre</h2>
          <dl class="mt-3 grid gap-3">
            {#each livre as i}
              <div><dt class="text-sm text-muted-foreground">{i.nom}</dt><dd class="mt-0.5 max-w-prose first-letter:uppercase">{i.texte}</dd></div>
            {/each}
          </dl>
        </section>
      {/if}

      <div class="mt-10 flex flex-wrap gap-2">
        <Button size="lg" href={`#/cocktail/${r.id}/preparer?${lienPreparer}`}><Martini class="size-4" aria-hidden="true" /> Préparer</Button>
        <Button size="lg" variant="outline" onclick={() => (edition = true)}>Corriger</Button>
        {#if r.etat === 'a_verifier'}
          <Button size="lg" variant="ghost" onclick={ignorer}>Ce n'est pas une recette</Button>
        {/if}
      </div>
    </div>
  </article>
{/if}
