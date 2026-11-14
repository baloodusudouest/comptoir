<script>
  // Fiche d'un cocktail : le livre et la page du livre papier pour le retrouver sur l'étagère,
  // les lieux, les ingrédients (ce qui manque en orange) recalculés pour N verres, la préparation.
  import { onMount } from 'svelte'
  import ArrowLeft from '@lucide/svelte/icons/arrow-left'
  import Star from '@lucide/svelte/icons/star'
  import Minus from '@lucide/svelte/icons/minus'
  import Plus from '@lucide/svelte/icons/plus'
  import Martini from '@lucide/svelte/icons/martini'
  import { api } from '$lib/api.js'
  import { recharger, quantite } from '$lib/donnees.svelte.js'
  import { Button } from '$lib/components/ui/button/index.js'
  import Vignette from '$lib/components/Vignette.svelte'
  import Editeur from '$lib/components/Editeur.svelte'

  let { id, session } = $props()
  let r = $state(null)
  let erreur = $state('')
  let verres = $state(1)
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
      <p class="mt-3 text-muted-foreground">{r.livre}{#if r.pages}, <span class="text-foreground">{r.pages}</span>{/if}</p>
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
          <div class="flex items-center gap-1 rounded-full border p-1" role="group" aria-label="Nombre de verres">
            <button type="button" class="grid size-8 place-items-center rounded-full hover:bg-secondary disabled:opacity-40" aria-label="Un verre de moins" disabled={verres <= 1} onclick={() => verres--}><Minus class="size-4" /></button>
            <span class="min-w-20 text-center text-sm tabular-nums">{verres} {verres > 1 ? 'verres' : 'verre'}</span>
            <button type="button" class="grid size-8 place-items-center rounded-full hover:bg-secondary disabled:opacity-40" aria-label="Un verre de plus" disabled={verres >= 8} onclick={() => verres++}><Plus class="size-4" /></button>
          </div>
        </div>
        <ul class="mt-3 divide-y">
          {#each r.lignes as l}
            <li class="flex items-baseline gap-3 py-2.5">
              <span class="w-24 shrink-0 text-right tabular-nums text-muted-foreground">{quantite(l.quantite, verres)} {l.unite}</span>
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

      <div class="mt-10 flex flex-wrap gap-2">
        <Button size="lg" href={`#/cocktail/${r.id}/preparer?verres=${verres}`}><Martini class="size-4" aria-hidden="true" /> Préparer</Button>
        <Button size="lg" variant="outline" onclick={() => (edition = true)}>Corriger</Button>
        {#if r.etat === 'a_verifier'}
          <Button size="lg" variant="ghost" onclick={ignorer}>Ce n'est pas une recette</Button>
        {/if}
      </div>
    </div>
  </article>
{/if}
