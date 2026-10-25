<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { api } from '$lib/api/commands';
  import { isTauri } from '$lib/api/client';
  import type { SystemStatus } from '$lib/api/types';
  import Icon from '$lib/components/Icon.svelte';
  import { isAuthenticated, login } from '$lib/stores/auth';

  let email = $state('');
  let password = $state('');
  let showPassword = $state(false);
  let submitting = $state(false);
  let error = $state<string | null>(null);

  let dbDialogOpen = $state(false);
  let dbUri = $state('');
  let dbName = $state('finance_app');
  let showDbUri = $state(false);
  let dbSaving = $state(false);
  let dbError = $state<string | null>(null);
  let dbSuccess = $state<string | null>(null);
  let dbStatus = $state<SystemStatus | null>(null);
  let dbSetupDismissed = $state(false);

  const features: Array<{ icon: 'wallet' | 'chart' | 'lock'; text: string }> = [
    { icon: 'wallet', text: 'Banyak dompet, satu saldo total yang jelas' },
    { icon: 'chart', text: 'Grafik arus kas dan kategori pengeluaran' },
    { icon: 'lock', text: 'Data tersimpan di MongoDB Atlas milik Anda' }
  ];

  onMount(() => {
    if (!isTauri()) return;
    void loadDatabaseStatus();
  });

  $effect(() => {
    if ($isAuthenticated) void goto('/dashboard', { replaceState: true });
  });

  async function loadDatabaseStatus() {
    try {
      const status = await api.systemStatus();
      dbStatus = status;
      if (status.config_source === 'missing' && !dbDialogOpen && !dbSetupDismissed) {
        openDatabaseDialog();
      }
    } catch {
      // The login form still works; the setup button remains available.
    }
  }

  function openDatabaseDialog() {
    dbError = null;
    dbSuccess = null;
    dbName = dbStatus?.db_name ?? (dbName.trim() || 'finance_app');
    dbDialogOpen = true;
  }

  function closeDatabaseDialog() {
    if (dbSaving) return;
    dbDialogOpen = false;
    dbSetupDismissed = true;
    dbError = null;
    dbSuccess = null;
    showDbUri = false;
  }

  function handleDbKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape' && dbDialogOpen && !dbSaving) closeDatabaseDialog();
  }

  async function saveDatabase(event: SubmitEvent) {
    event.preventDefault();
    if (dbSaving) return;

    const uri = dbUri.trim();
    if (!uri.startsWith('mongodb://') && !uri.startsWith('mongodb+srv://')) {
      dbError = 'Connection string harus diawali mongodb:// atau mongodb+srv://.';
      return;
    }
    if (uri.length < 12 || uri.length > 2048) {
      dbError = 'Panjang connection string tidak valid.';
      return;
    }

    const name = dbName.trim() || 'finance_app';
    if (!/^[A-Za-z0-9_-]{1,64}$/.test(name)) {
      dbError =
        'Nama database hanya boleh berisi huruf, angka, garis bawah, atau tanda hubung (maks. 64 karakter).';
      return;
    }

    dbSaving = true;
    dbError = null;
    dbSuccess = null;
    try {
      const status = await api.setMongoConnection(uri, name);
      dbStatus = status;
      dbUri = '';
      dbSuccess = 'Koneksi database berhasil disimpan. Memuat ulang aplikasi…';
      setTimeout(() => window.location.reload(), 900);
    } catch (caught) {
      dbError = caught instanceof Error ? caught.message : 'Gagal menyimpan koneksi database.';
    } finally {
      dbSaving = false;
    }
  }

  async function handleSubmit(event: SubmitEvent) {
    event.preventDefault();
    if (submitting) return;
    submitting = true;
    error = null;
    try {
      await login({ email: email.trim(), password });
      await goto('/dashboard', { replaceState: true });
    } catch (caught) {
      error = caught instanceof Error ? caught.message : 'Gagal masuk. Silakan coba lagi.';
    } finally {
      submitting = false;
    }
  }

  function fillDemo() {
    email = 'demo@finance.app';
    password = 'demo12345';
  }
</script>

<svelte:window onkeydown={handleDbKeydown} />

<div class="grid min-h-screen lg:grid-cols-[1.05fr_1fr]">
  <section
    class="relative hidden overflow-hidden bg-neutral p-12 text-neutral-content lg:flex lg:flex-col"
  >
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
        <p class="text-[11px] uppercase tracking-[0.16em] text-neutral-content/45">
          Personal money
        </p>
      </div>
    </div>

    <div class="relative my-auto max-w-lg py-16">
      <span
        class="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-[11px] font-medium text-neutral-content/70"
      >
        <Icon name="sparkles" size={13} />
        Keuangan pribadi, tanpa ribet
      </span>
      <h1 class="mt-6 text-4xl font-semibold leading-[1.12] tracking-tight xl:text-5xl">
        Semua uang Anda.<br />
        <span class="text-primary">Satu tempat yang rapi.</span>
      </h1>
      <p class="mt-5 max-w-md text-sm leading-relaxed text-neutral-content/60">
        Catat pemasukan dan pengeluaran, pantau saldo tiap dompet, dan lihat ke mana uang Anda pergi
        — dalam aplikasi desktop yang cepat dan privat.
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

  <section class="flex items-center justify-center px-5 py-8 sm:px-10">
    <div class="w-full max-w-sm">
      <div class="mb-6 flex items-center gap-3 lg:hidden">
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

      <h2 class="text-2xl font-semibold tracking-tight">Selamat datang kembali</h2>
      <p class="mt-1.5 text-sm text-base-content/50">Masuk untuk melanjutkan mengelola keuangan.</p>

      {#if isTauri() && dbStatus && !dbStatus.db_connected && dbStatus.config_source !== 'missing'}
        <div class="mt-4 rounded-xl border border-warning/25 bg-warning/10 p-3" role="status">
          <div class="flex items-start gap-2.5">
            <span
              class="mt-0.5 grid size-7 shrink-0 place-items-center rounded-lg bg-warning/15 text-warning"
            >
              <Icon name="alert" size={14} />
            </span>
            <div class="min-w-0 flex-1">
              <p class="text-[11px] font-semibold text-warning-content">Database belum terhubung</p>
              <p class="mt-0.5 line-clamp-2 text-[11px] leading-relaxed text-base-content/50">
                {dbStatus.last_error ?? 'Periksa connection string dan whitelist IP Atlas.'}
              </p>
            </div>
            <button type="button" class="btn btn-warning btn-xs" onclick={openDatabaseDialog}>
              Atur
            </button>
          </div>
        </div>
      {/if}

      <form class="mt-6 space-y-4" onsubmit={handleSubmit}>
        <label class="block">
          <span class="mb-1.5 block text-xs font-medium text-base-content/60">Email</span>
          <span
            class="input input-bordered flex w-full items-center gap-2 focus-within:border-primary"
          >
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
          <span
            class="input input-bordered flex w-full items-center gap-2 focus-within:border-primary"
          >
            <Icon name="lock" size={16} class="text-base-content/35" />
            <input
              type={showPassword ? 'text' : 'password'}
              class="grow border-0 bg-transparent text-sm outline-none"
              placeholder="••••••••"
              autocomplete="current-password"
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
          Masuk
          {#if !submitting}
            <Icon name="arrow-right" size={16} />
          {/if}
        </button>
      </form>

      {#if isTauri()}
        <div class="mt-4 rounded-xl border border-base-content/10 bg-base-100/60 p-3">
          <div class="flex items-start gap-2.5">
            <span
              class="mt-0.5 grid size-7 shrink-0 place-items-center rounded-lg {dbStatus?.db_connected
                ? 'bg-success/12 text-success'
                : 'bg-warning/15 text-warning'}"
            >
              <Icon name="database" size={14} />
            </span>
            <div class="min-w-0 flex-1">
              <p class="text-[11px] font-semibold text-base-content/65">Database MongoDB</p>
              <p class="mt-0.5 truncate text-[11px] text-base-content/45">
                {#if dbStatus?.db_connected}
                  Terhubung ke {dbStatus.db_name}
                {:else if dbStatus?.config_source === 'missing'}
                  Belum dikonfigurasi
                {:else}
                  Belum terhubung
                {/if}
              </p>
            </div>
            <button
              type="button"
              class="btn btn-ghost btn-xs text-primary"
              onclick={openDatabaseDialog}
            >
              {dbStatus?.db_connected ? 'Ubah' : 'Atur'}
            </button>
          </div>
        </div>
      {/if}

      {#if !isTauri()}
        <div class="mt-5 rounded-xl border border-dashed border-base-content/12 bg-base-100/60 p-3">
          <p class="text-[11px] leading-relaxed text-base-content/50">
            Mode demo browser. Gunakan akun <span class="font-semibold">demo@finance.app</span> /
            <span class="font-semibold">demo12345</span>.
          </p>
          <button
            type="button"
            class="btn btn-ghost btn-xs mt-1 px-0 text-primary"
            onclick={fillDemo}
          >
            Isi akun demo
            <Icon name="arrow-right" size={12} />
          </button>
        </div>
      {/if}

      <p class="mt-6 text-center text-xs text-base-content/45">
        Belum punya akun?
        <a href="/register" class="font-semibold text-primary hover:underline">Daftar sekarang</a>
      </p>
    </div>
  </section>
</div>

{#if dbDialogOpen}
  <div class="fixed inset-0 z-[110] grid place-items-center p-4">
    <button
      type="button"
      class="absolute inset-0 bg-black/50 backdrop-blur-sm"
      aria-label="Tutup dialog"
      onclick={closeDatabaseDialog}
    ></button>

    <div
      class="modal-panel surface relative max-h-[92vh] w-full max-w-md overflow-y-auto p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="db-setup-title"
    >
      <div class="flex items-start justify-between gap-4">
        <div class="flex items-center gap-3">
          <span class="grid size-10 place-items-center rounded-2xl bg-primary/12 text-primary">
            <Icon name="database" size={19} />
          </span>
          <div>
            <h2 id="db-setup-title" class="text-lg font-semibold tracking-tight">
              Hubungkan database
            </h2>
            <p class="text-xs text-base-content/45">
              MongoDB Atlas untuk menyimpan data akun dan transaksi.
            </p>
          </div>
        </div>
        <button
          type="button"
          class="btn btn-ghost btn-sm btn-circle"
          aria-label="Tutup"
          disabled={dbSaving}
          onclick={closeDatabaseDialog}
        >
          <Icon name="close" size={18} />
        </button>
      </div>

      {#if dbStatus?.db_uri_masked}
        <p
          class="mt-4 rounded-xl border border-base-content/8 bg-base-200/60 px-3 py-2 text-[11px] text-base-content/45"
        >
          Koneksi tersimpan:
          <span class="ml-1 break-all font-mono text-base-content/65">{dbStatus.db_uri_masked}</span
          >
        </p>
      {/if}

      <form class="mt-5 space-y-4" onsubmit={saveDatabase}>
        <label class="block">
          <span class="mb-1.5 block text-xs font-medium text-base-content/60"
            >Connection string</span
          >
          <span
            class="input input-bordered flex w-full items-center gap-2 focus-within:border-primary"
          >
            <Icon name="database" size={15} class="shrink-0 text-base-content/35" />
            <input
              type={showDbUri ? 'text' : 'password'}
              class="grow border-0 bg-transparent font-mono text-xs outline-none"
              placeholder="mongodb+srv://user:password@cluster…"
              maxlength="2048"
              autocomplete="off"
              spellcheck="false"
              disabled={dbSaving}
              bind:value={dbUri}
              required
            />
            <button
              type="button"
              class="btn btn-ghost btn-xs btn-circle text-base-content/35"
              aria-label={showDbUri
                ? 'Sembunyikan connection string'
                : 'Tampilkan connection string'}
              disabled={dbSaving}
              onclick={() => (showDbUri = !showDbUri)}
            >
              <Icon name={showDbUri ? 'eye-off' : 'eye'} size={14} />
            </button>
          </span>
        </label>

        <label class="block">
          <span class="mb-1.5 block text-xs font-medium text-base-content/60">Nama database</span>
          <input
            type="text"
            class="input input-bordered w-full font-mono text-xs"
            placeholder="finance_app"
            maxlength="64"
            autocomplete="off"
            spellcheck="false"
            disabled={dbSaving}
            bind:value={dbName}
          />
        </label>

        {#if dbError}
          <div class="alert alert-error py-2 text-xs" role="alert">
            <Icon name="alert" size={15} />
            <span>{dbError}</span>
          </div>
        {/if}

        {#if dbSuccess}
          <div class="alert alert-success py-2 text-xs" role="status">
            <Icon name="check" size={15} />
            <span>{dbSuccess}</span>
          </div>
        {/if}

        <div
          class="rounded-xl border border-base-content/8 bg-base-200/60 p-3 text-[11px] leading-relaxed text-base-content/50"
        >
          Pastikan IP perangkat ini diizinkan di
          <span class="font-semibold text-base-content/65">Atlas → Network Access</span>, dan user
          database punya akses <span class="font-mono">readWrite</span> ke database ini.
        </div>

        <div class="flex justify-end gap-2 pt-1">
          <button
            type="button"
            class="btn btn-ghost"
            disabled={dbSaving}
            onclick={closeDatabaseDialog}
          >
            Batal
          </button>
          <button type="submit" class="btn btn-primary" disabled={dbSaving || !dbUri.trim()}>
            {#if dbSaving}
              <span class="loading loading-spinner loading-xs"></span>
            {/if}
            Uji & simpan
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}
