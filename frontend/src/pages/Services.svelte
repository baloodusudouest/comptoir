<script>
  // « Connexion » : une tuile par service extérieur (Wikidata, Mistral), avec son voyant. Toucher une tuile ouvre le
  // service : ce que Comptoir y lit, ce qu'il y écrit, le réglage de la stack, les derniers appels et « Vérifier ».
  // (pages/Connexion.svelte est la page du mot de passe : ne pas confondre.)
  import { onMount } from 'svelte'
  import Globe from '@lucide/svelte/icons/globe'
  import Sparkles from '@lucide/svelte/icons/sparkles'
  import { api } from '$lib/api.js'
  import { Button } from '$lib/components/ui/button/index.js'

  const icones = { wikidata: Globe, mistral: Sparkles }
  const statuts = { ok: 'réussi', erreur: 'échec', absent: 'rien trouvé', refuse: 'refusé' }

  let sources = $state([])
  let choisi = $state(null)
  let verifs = $state({})
  let erreur = $state('')

  let service = $derived(sources.find((s) => s.id === choisi))

  async function verifier(s) {
    verifs[s.id] = { message: 'Vérification…' }
    try { verifs[s.id] = await api.post(`/api/sources/${s.id}/verifier`) }
    catch (e) { verifs[s.id] = { ok: false, message: e.message } }
  }
  onMount(async () => {
    try { sources = await api.get('/api/sources') } catch (e) { erreur = e.message }
  })
</script>

<h1 class="titre mb-6">Connexion</h1>

{#if erreur}<p class="text-destructive" role="alert">{erreur}</p>{/if}

<div class="grid max-w-3xl grid-cols-2 gap-3 md:grid-cols-3">
  {#each sources as s (s.id)}
    {@const Icone = icones[s.id] ?? Globe}
    <button type="button" aria-pressed={choisi === s.id} onclick={() => (choisi = choisi === s.id ? null : s.id)}
            class="flex min-h-28 flex-col gap-1 rounded-2xl border bg-card p-4 text-left transition-colors hover:border-primary aria-pressed:border-primary">
      <span class="flex items-start justify-between">
        <Icone class="size-6 text-primary" aria-hidden="true" />
        <span class={`size-2.5 rounded-full ${s.actif ? 'bg-valide' : 'bg-muted-foreground/40'}`} aria-hidden="true"></span>
      </span>
      <span class="font-medium">{s.nom}</span>
      <span class="text-sm text-muted-foreground">{s.actif ? 'actif' : 'coupé dans la stack'}</span>
    </button>
  {/each}
</div>

{#if service}
  <section class="mt-4 max-w-3xl rounded-2xl border bg-card p-5" aria-labelledby="titre-service">
    <div class="flex flex-wrap items-center justify-between gap-3">
      <h2 id="titre-service" class="text-lg font-semibold">{service.nom}</h2>
      <Button variant="outline" onclick={() => verifier(service)}>Vérifier</Button>
    </div>
    <p class="mt-1 text-sm text-muted-foreground">{service.role}</p>
    {#if verifs[service.id]}
      <p class={`mt-2 text-sm ${verifs[service.id].ok ? 'text-valide' : verifs[service.id].ok === false ? 'text-destructive' : ''}`} role="status">{verifs[service.id].message}</p>
    {/if}
    <dl class="mt-4 grid gap-3 text-sm sm:grid-cols-[8rem_1fr]">
      <dt class="text-muted-foreground">Ce qu'il lit</dt><dd>{service.lit}</dd>
      <dt class="text-muted-foreground">Ce qu'il écrit</dt><dd>{service.ecrit}</dd>
      <dt class="text-muted-foreground">Réglage</dt>
      <dd><code class="rounded bg-secondary px-1.5 py-0.5">{service.reglage}</code>{service.actif ? '' : ' : à remplir dans la stack Portainer pour l\'activer'}</dd>
    </dl>
    <h3 class="mt-5 text-sm font-medium">Derniers appels</h3>
    {#if service.derniers.length}
      <ul class="mt-1 divide-y text-sm">
        {#each service.derniers as d}
          <li class="flex flex-wrap justify-between gap-x-4 py-2">
            <span class="min-w-0">{d.cible} <span class="text-muted-foreground">({statuts[d.statut] ?? d.statut})</span></span>
            <time class="text-muted-foreground tabular-nums" datetime={d.le}>{new Date(d.le).toLocaleString('fr-FR', { dateStyle: 'short', timeStyle: 'short' })}</time>
          </li>
        {/each}
      </ul>
    {:else}
      <p class="mt-1 text-sm text-muted-foreground">Aucun appel pour l'instant.</p>
    {/if}
  </section>
{:else if sources.length}
  <p class="mt-4 text-sm text-muted-foreground">Touche un service pour voir ce que Comptoir y lit et y écrit.</p>
{/if}
