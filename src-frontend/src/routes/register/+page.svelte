<script lang="ts">
  import { goto } from '$app/navigation';
  import Icon from '$lib/components/Icon.svelte';
  import { isAuthenticated, register } from '$lib/stores/auth';

  let name = $state('');
  let email = $state('');
  let password = $state('');
  let confirm = $state('');
  let currency = $state('IDR');
  let showPassword = $state(false);
  let submitting = $state(false);
  let error = $state<string | null>(null);

  const features: Array<{ icon: 'wallet' | 'chart' | 'lock'; text: string }> = [
    { icon: 'wallet', text: 'Dompet tak terbatas untuk tunai, bank, dan e-wallet' },
    { icon: 'chart', text: 'Ringkasan bulanan dan mingguan yang otomatis' },
    { icon: 'lock', text: 'Password di-hash dengan Argon2id, sesi memakai JWT' }
  ];

  $effect(() => {
    if ($isAuthenticated) void goto('/dashboard', { replaceState: true });
  });

  async function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    if (submitting) return;
    if (password.length < 8) {
      error = 'Password minimal 8 karakter.';
      return;
    }
    if (password !== confirm) {
      error = 'Konfirmasi password tidak cocok.';
      return;
    }

    submitting = true;
    error = null;
    try {
      await register({
        email: email.trim(),
        name: name.trim(),
        password,
        base_currency: currency
      });
      await goto('/dashboard', { replaceState: true });
    } catch (caught) {
      error = caught instanceof Error ? caught.message : 'Gagal mendaftar. Silakan coba lagi.';
    } finally {
      submitting = false;
    }
  }
</script>

<div class="grid min-h-screen lg:grid-cols-[1.05fr_1fr]">
  <section class="relative hidden overflow-hidden bg-neutral p-12 text-neutral-content lg:flex lg:flex-col">
    <div
      class="pointer-events-none absolute inset-0 bg-[radial-gradient(800px_500px_at_15%_10%,rgba(16,185,129,0.32),transparent_60%),radial-gradient(700px_500px_at_90%_90%,rgba(99,102,241,0.28),transparent_55%)]"
      aria-hidden="true"
    ></div>
    <div class="pointer-events-none absolute inset-0 opacity-[0.06]" aria-hidden="true">
      <div
        class="h-full w-full bg-[linear-gradient(rgba(255,255,255,0.6)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.6)_1px,transparent_1px)] bg-[size:56px_56px]"
      ></div>
    </div>

    <div class="relative flex items-center gap-3">
      <span
        class="grid size-11 place-items-center rounded-2xl bg-gradient-to-br from-primary to-secondary text-primary-content shadow-lg shadow-black/20"
      >
        <Icon name="chart" size={22} strokeWidth={2.2} />
      </span>
      <div>
        <p class="text-[15px] font-semibold tracking-tight">FinanceApp</p>
        <p class="text-[11px] uppercase tracking-[0.16em] text-neutral-content/45">Personal money</p>
      </div>
    </div>

    <div class="relative my-auto max-w-lg py-16">
      <span
        class="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[11px] font-medium text-neutral-content/70"
      >
        <Icon name="sparkles" size={13} />
        Mulai dalam satu menit
      </span>
      <h1 class="mt-6 text-4xl font-semibold leading-[1.12] tracking-tight xl:text-5xl">
        Mulai rapi.<br />
        <span class="text-primary">Mulai dari sini.</span>
      </h1>
      <p class="mt-5 max-w-md text-sm leading-relaxed text-neutral-content/60">
        Buat akun, tambahkan dompet pertama Anda, dan biarkan FinanceApp menghitung sisanya.
      </p>

      <ul class="mt-9 space-y-3.5">
        {#each features as feature (feature.text)}
          <li class="flex items-center gap-3 text-sm text-neutral-content/75">
            <span class="grid size-8 place-items-center rounded-xl bg-white/8 text-primary">
              <Icon name={feature.icon} size={16} />
            </span>
            {feature.text}
          </li>
        {/each}
      </ul>
    </div>

    <p class="relative text-[11px] text-neutral-content/35">
      FinanceApp · Desktop personal finance · v0.1.0
    </p>
  </section>

  <section class="flex items-center justify-center px-5 py-10 sm:px-10">
    <div class="w-full max-w-sm">
      <div class="mb-8 flex items-center gap-3 lg:hidden">
        <span
          class="grid size-10 place-items-center rounded-2xl bg-gradient-to-br from-primary to-secondary text-primary-content shadow-lg shadow-primary/20"
        >
          <Icon name="chart" size={20} strokeWidth={2.2} />
        </span>
        <div>
          <p class="text-sm font-semibold tracking-tight">FinanceApp</p>
          <p class="text-[10px] uppercase tracking-[0.14em] text-base-content/40">Personal money</p>
        </div>
      </div>

      <h2 class="text-2xl font-semibold tracking-tight">Buat akun baru</h2>
      <p class="mt-1.5 text-sm text-base-content/50">Gratis, cepat, dan data tetap milik Anda.</p>

      <form class="mt-7 space-y-3.5" onsubmit={handleSubmit}>
        <label class="block">
          <span class="mb-1.5 block text-xs font-medium text-base-content/60">Nama</span>
          <span class="input input-bordered flex w-full items-center gap-2 focus-within:border-primary">
            <Icon name="user" size={16} class="text-base-content/35" />
            <input
              type="text"
              class="grow border-0 bg-transparent text-sm outline-none"
              placeholder="Nama lengkap"
              autocomplete="name"
              maxlength="80"
              bind:value={name}
              required
            />
          </span>
        </label>

        <label class="block">
          <span class="mb-1.5 block text-xs font-medium text-base-content/60">Email</span>
          <span class="input input-bordered flex w-full items-center gap-2 focus-within:border-primary">
            <Icon name="mail" size={16} class="text-base-content/35" />
            <input
              type="email"
              class="grow border-0 bg-transparent text-sm outline-none"
              placeholder="nama@email.com"
              autocomplete="email"
              bind:value={email}
              required
            />
          </span>
        </label>

        <label class="block">
          <span class="mb-1.5 block text-xs font-medium text-base-content/60">Password</span>
          <span class="input input-bordered flex w-full items-center gap-2 focus-within:border-primary">
            <Icon name="lock" size={16} class="text-base-content/35" />
            <input
              type={showPassword ? 'text' : 'password'}
              class="grow border-0 bg-transparent text-sm outline-none"
              placeholder="Minimal 8 karakter"
              autocomplete="new-password"
              minlength="8"
              bind:value={password}
              required
            />
            <button
              type="button"
              class="btn btn-ghost btn-xs btn-circle text-base-content/35"
              aria-label={showPassword ? 'Sembunyikan password' : 'Tampilkan password'}
              onclick={() => (showPassword = !showPassword)}
            >
              <Icon name={showPassword ? 'eye-off' : 'eye'} size={15} />
            </button>
          </span>
        </label>

        <label class="block">
          <span class="mb-1.5 block text-xs font-medium text-base-content/60">Konfirmasi password</span>
          <span class="input input-bordered flex w-full items-center gap-2 focus-within:border-primary">
            <Icon name="lock" size={16} class="text-base-content/35" />
            <input
              type={showPassword ? 'text' : 'password'}
              class="grow border-0 bg-transparent text-sm outline-none"
              placeholder="Ulangi password"
              autocomplete="new-password"
              bind:value={confirm}
              required
            />
          </span>
        </label>

        <label class="block">
          <span class="mb-1.5 block text-xs font-medium text-base-content/60">Mata uang utama</span>
          <select class="select select-bordered w-full text-sm" bind:value={currency}>
            <option value="IDR">IDR — Rupiah Indonesia</option>
            <option value="USD">USD — US Dollar</option>
            <option value="EUR">EUR — Euro</option>
            <option value="SGD">SGD — Singapore Dollar</option>
          </select>
        </label>

        {#if error}
          <div class="alert alert-error py-2 text-xs" role="alert">
            <Icon name="alert" size={15} />
            <span>{error}</span>
          </div>
        {/if}

        <button type="submit" class="btn btn-primary w-full" disabled={submitting}>
          {#if submitting}
            <span class="loading loading-spinner loading-xs"></span>
          {/if}
          Buat akun
          {#if !submitting}
            <Icon name="arrow-right" size={16} />
          {/if}
        </button>
      </form>

      <p class="mt-7 text-center text-xs text-base-content/45">
        Sudah punya akun?
        <a href="/login" class="font-semibold text-primary hover:underline">Masuk</a>
      </p>
    </div>
  </section>
</div>
