<script>
  // Signature de Comptoir : un fin cercle de zeste d'orange autour du nombre de cocktails faisables.
  // L'arc rempli montre la part des recettes qu'on peut faire ce soir.
  let { valeur = 0, total = 0, libelle = '' } = $props()
  const r = 54
  const tour = 2 * Math.PI * r
  let part = $derived(total ? Math.min(1, valeur / total) : 0)
</script>

<figure class="relative grid size-40 shrink-0 place-items-center" aria-label={`${valeur} ${libelle}`}>
  <svg viewBox="0 0 128 128" class="absolute inset-0 -rotate-90" aria-hidden="true">
    <circle cx="64" cy="64" r={r} fill="none" stroke="currentColor" class="text-border" stroke-width="2" />
    <circle cx="64" cy="64" r={r} fill="none" stroke="var(--app)" stroke-width="5" stroke-linecap="round"
            stroke-dasharray={`${tour * part} ${tour}`} style="transition: stroke-dasharray .6s ease" />
    <!-- les pores du zeste -->
    {#each Array(28) as _, i}
      {@const a = (i / 28) * Math.PI * 2}
      <circle cx={64 + Math.cos(a) * (r + 7)} cy={64 + Math.sin(a) * (r + 7)} r="0.9" fill="var(--app)" opacity={i / 28 < part ? 0.7 : 0.18} />
    {/each}
  </svg>
  <figcaption class="text-center">
    <span class="chiffre block text-5xl">{valeur}</span>
    <span class="mt-1 block text-xs text-muted-foreground">{libelle}</span>
  </figcaption>
</figure>
