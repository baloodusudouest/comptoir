<script>
  // Combien en préparer : un nombre de verres (1 à 50), ou un volume en litres (pour un pichet, un punch).
  // En litres, le facteur = volume voulu ÷ volume d'un verre (ingrédients mesurés, avant la glace), et l'équivalent
  // en verres est affiché. Sans ingrédient mesurable (tout « compléter avec… »), seul le nombre de verres est proposé.
  // Partagé par la fiche et le mode Préparer ; « facteur » est lié (bind:facteur), « reglage » aussi (pour l'adresse).
  import Minus from '@lucide/svelte/icons/minus'
  import Plus from '@lucide/svelte/icons/plus'
  import { volumeVerre } from '$lib/donnees.svelte.js'

  let { lignes = [], facteur = $bindable(1), reglage = $bindable({ mode: 'verres', verres: 1, litres: 1 }), grand = false } = $props()

  const VERRES_MAX = 50, LITRES_MIN = 0.1, LITRES_MAX = 20
  let parVerre = $derived(volumeVerre(lignes))           // cl
  let mode = $state(reglage.mode)
  let verres = $state(reglage.verres)
  let litres = $state(reglage.litres)
  let saisie = $state(String(reglage.litres).replace('.', ','))

  $effect(() => {
    const m = parVerre > 0 ? mode : 'verres'
    facteur = m === 'litres' ? (litres * 100) / parVerre : verres
    reglage = { mode: m, verres, litres }
  })

  const borner = (v, a, b) => Math.min(b, Math.max(a, v))
  function changerLitres(delta) {
    litres = Math.round(borner(litres + delta, LITRES_MIN, LITRES_MAX) * 100) / 100
    saisie = String(litres).replace('.', ',')
  }
  function lireSaisie() {
    const v = parseFloat(saisie.replace(',', '.'))
    if (Number.isFinite(v)) litres = Math.round(borner(v, LITRES_MIN, LITRES_MAX) * 100) / 100
    saisie = String(litres).replace('.', ',')
  }
  const fmt = (v) => String(Math.round(v * 10) / 10).replace('.', ',')
  let bouton = $derived(grand ? 'size-10' : 'size-8')
  let icone = $derived(grand ? 'size-5' : 'size-4')
</script>

<div class="flex flex-wrap items-center justify-end gap-2">
  {#if parVerre > 0}
    <div class="flex rounded-full border p-0.5 text-sm" role="group" aria-label="Préparer en">
      {#each [['verres', 'Verres'], ['litres', 'Litres']] as [m, nom]}
        <button type="button" aria-pressed={mode === m} onclick={() => (mode = m)}
                class={`rounded-full px-3 text-muted-foreground aria-pressed:bg-secondary aria-pressed:text-foreground ${grand ? 'h-10' : 'h-8'}`}>{nom}</button>
      {/each}
    </div>
  {/if}

  {#if mode === 'litres' && parVerre > 0}
    <div class="flex items-center gap-1 rounded-full border p-1" role="group" aria-label="Volume à préparer">
      <button type="button" class={`grid ${bouton} place-items-center rounded-full hover:bg-secondary disabled:opacity-40`} aria-label="Un quart de litre de moins"
              disabled={litres <= LITRES_MIN} onclick={() => changerLitres(litres > 0.25 ? -0.25 : -0.05)}><Minus class={icone} /></button>
      <label class="flex items-center gap-1 tabular-nums">
        <span class="sr-only">Litres</span>
        <input type="text" inputmode="decimal" bind:value={saisie} onchange={lireSaisie} onblur={lireSaisie}
               class="w-14 bg-transparent text-right outline-none focus-visible:underline" aria-label="Nombre de litres" />
        <span>l</span>
      </label>
      <button type="button" class={`grid ${bouton} place-items-center rounded-full hover:bg-secondary disabled:opacity-40`} aria-label="Un quart de litre de plus"
              disabled={litres >= LITRES_MAX} onclick={() => changerLitres(0.25)}><Plus class={icone} /></button>
    </div>
    <p class="w-full text-right text-sm text-muted-foreground" role="status">
      ≈ {fmt(facteur)} verre{facteur >= 2 ? 's' : ''} de {fmt(parVerre)} cl, avant la glace
    </p>
  {:else}
    <div class="flex items-center gap-1 rounded-full border p-1" role="group" aria-label="Nombre de verres">
      <button type="button" class={`grid ${bouton} place-items-center rounded-full hover:bg-secondary disabled:opacity-40`} aria-label="Un verre de moins"
              disabled={verres <= 1} onclick={() => verres--}><Minus class={icone} /></button>
      <span class="min-w-20 text-center tabular-nums">{verres} {verres > 1 ? 'verres' : 'verre'}</span>
      <button type="button" class={`grid ${bouton} place-items-center rounded-full hover:bg-secondary disabled:opacity-40`} aria-label="Un verre de plus"
              disabled={verres >= VERRES_MAX} onclick={() => verres++}><Plus class={icone} /></button>
    </div>
  {/if}
</div>
