<script>
  // Mode Préparer : plein écran, une étape à la fois, en grand. Ingrédients à cocher, quantités pour N verres,
  // écran maintenu allumé, boutons larges et balayage pour avancer (mains mouillées).
  // Une colonne sur téléphone ; ingrédients | étape à partir de la largeur d'une tablette.
  import { onMount } from 'svelte'
  import X from '@lucide/svelte/icons/x'
  import Minus from '@lucide/svelte/icons/minus'
  import Plus from '@lucide/svelte/icons/plus'
  import Check from '@lucide/svelte/icons/check'
  import { api } from '$lib/api.js'
  import { quantite } from '$lib/donnees.svelte.js'

  let { id } = $props()
  let r = $state(null)
  let verres = $state(Math.min(8, Math.max(1, Number(new URLSearchParams(location.hash.split('?')[1] || '').get('verres')) || 1)))
  let etape = $state(0)
  let coches = $state(new Set())
  let eveille = $state('')          // « Écran maintenu allumé » ou la raison de l'échec
  let verrou = null

  let etapes = $derived(r ? (r.etapes.length ? r.etapes : ['Assembler les ingrédients et servir.']) : [])

  async function garderAllume() {
    if (!window.isSecureContext) {
      // Le navigateur ne garde l'écran allumé que sur une adresse en HTTPS (Tailscale Serve, par exemple)
      eveille = "L'écran ne peut rester allumé que si Comptoir est ouvert en HTTPS : règle la mise en veille de l'appareil, ou ouvre l'adresse HTTPS."
      return
    }
    try {
      verrou = await navigator.wakeLock.request('screen')
      eveille = 'Écran maintenu allumé'
    } catch {
      // Navigateur sans Wake Lock (iOS avant 16.4) ou demande refusée : on le dit, sans bricolage
      eveille = "Ce navigateur ne peut pas garder l'écran allumé : règle la mise en veille de l'appareil."
    }
  }
  function cocher(i) {
    const n = new Set(coches)
    n.has(i) ? n.delete(i) : n.add(i)
    coches = n
  }
  function suivant() { if (etape < etapes.length - 1) etape++ }
  function precedent() { if (etape > 0) etape-- }

  let debutX = null
  function toucher(e) { debutX = e.touches[0].clientX }
  function relacher(e) {
    if (debutX == null) return
    const d = e.changedTouches[0].clientX - debutX
    if (Math.abs(d) > 60) (d < 0 ? suivant : precedent)()
    debutX = null
  }

  onMount(async () => {
    r = await api.get(`/api/recettes/${id}`)
    garderAllume()
    const reprise = () => document.visibilityState === 'visible' && garderAllume()
    document.addEventListener('visibilitychange', reprise)
    return () => { document.removeEventListener('visibilitychange', reprise); verrou?.release?.() }
  })
</script>

<svelte:window onkeydown={(e) => { if (e.key === 'ArrowRight') suivant(); if (e.key === 'ArrowLeft') precedent() }} />


{#if r}
  <div class="flex min-h-dvh flex-col px-[max(1rem,env(safe-area-inset-left))] pt-[calc(0.75rem+env(safe-area-inset-top))] pb-[calc(1rem+env(safe-area-inset-bottom))] md:px-8"
       ontouchstart={toucher} ontouchend={relacher} role="presentation">
    <header class="flex items-center justify-between gap-3">
      <a href={`#/cocktail/${r.id}`} class="flex h-11 items-center gap-1.5 rounded-full border px-4 text-sm"><X class="size-4" aria-hidden="true" /> Quitter</a>
      <div class="flex items-center gap-1 rounded-full border p-1" role="group" aria-label="Nombre de verres">
        <button type="button" class="grid size-10 place-items-center rounded-full hover:bg-secondary disabled:opacity-40" aria-label="Un verre de moins" disabled={verres <= 1} onclick={() => verres--}><Minus class="size-5" /></button>
        <span class="min-w-20 text-center tabular-nums">{verres} {verres > 1 ? 'verres' : 'verre'}</span>
        <button type="button" class="grid size-10 place-items-center rounded-full hover:bg-secondary disabled:opacity-40" aria-label="Un verre de plus" disabled={verres >= 8} onclick={() => verres++}><Plus class="size-5" /></button>
      </div>
    </header>

    <h1 class="carte-nom mt-5 text-2xl md:text-3xl">{r.titre}</h1>
    {#if eveille}<p class="mt-1 text-xs text-muted-foreground" role="status">{eveille}</p>{/if}

    <div class="mt-6 grid flex-1 gap-8 md:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] md:gap-12">
      <section aria-labelledby="titre-a-verser">
        <h2 id="titre-a-verser" class="sr-only">Ingrédients à verser</h2>
        <ul class="grid gap-2">
          {#each r.lignes as l, i}
            <li>
              <button type="button" role="checkbox" aria-checked={coches.has(i)} onclick={() => cocher(i)}
                      class="flex min-h-14 w-full items-center gap-4 rounded-2xl border px-4 py-3 text-left text-lg transition-colors aria-checked:border-transparent aria-checked:bg-secondary aria-checked:text-muted-foreground">
                <span class="grid size-7 shrink-0 place-items-center rounded-full border-2 border-primary" aria-hidden="true">
                  {#if coches.has(i)}<Check class="size-4 text-primary" />{/if}
                </span>
                <span class="min-w-0">
                  <span class="tabular-nums font-medium">{quantite(l.quantite, verres)} {l.unite}</span>
                  <span class={coches.has(i) ? 'line-through' : ''}>{l.nom || l.texte}</span>
                </span>
              </button>
            </li>
          {/each}
        </ul>
      </section>

      <section aria-labelledby="titre-etape" aria-live="polite" class="flex flex-col">
        <h2 id="titre-etape" class="text-muted-foreground">Étape {etape + 1} sur {etapes.length}</h2>
        <p class="etape-grande mt-3 max-w-[30ch]">{etapes[etape]}</p>
        <div class="mt-auto grid grid-cols-2 gap-3 pt-8">
          <button type="button" onclick={precedent} disabled={etape === 0}
                  class="h-16 rounded-2xl border text-lg disabled:opacity-35">Précédente</button>
          {#if etape < etapes.length - 1}
            <button type="button" onclick={suivant} class="h-16 rounded-2xl bg-primary text-lg font-medium text-primary-foreground">Suivante</button>
          {:else}
            <a href={`#/cocktail/${r.id}`} class="grid h-16 place-items-center rounded-2xl bg-primary text-lg font-medium text-primary-foreground">Santé !</a>
          {/if}
        </div>
      </section>
    </div>
  </div>
{/if}
