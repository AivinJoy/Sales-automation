<!-- sales-ui\src\routes\+page.svelte -->

<script lang="ts">
    import { onMount } from 'svelte';
    import { API_URL } from '$lib/config';
    import EverydayDashboard from '$lib/components/EverydayDashboard.svelte'; // Make sure this filename matches your actual file
    import HistoryBackfill from '$lib/components/HistoryBackfill.svelte';
    import ReportViewer from '$lib/components/Reports.svelte'; 

    let mode: 'dashboard' | 'simulation' = 'dashboard';
    let sidebarTab: 'sales' | 'purchases' = 'sales'; 
    
    // Inventory State
    let boxStock = 0;
    let liquidStock = 0;
    
    // Lists
    let reportsList: string[] = [];
    let purchasesList: string[] = [];
    
    let selectedReport: string | null = null; 

    async function fetchLiveStock() {
        try {
            const res = await fetch(`${API_URL}/state`);
            const data = await res.json();
            
            // Extract specific stocks
            const stockMap = data.stock_map || {};
            boxStock = stockMap["Soore Box"] || 0;
            liquidStock = stockMap["Soore Liquid"] || 0;

        } catch (e) { console.error("Backend offline?"); }
    }

    async function fetchLists() {
        try {
            const resSales = await fetch(`${API_URL}/reports/list`);
            reportsList = (await resSales.json()).files;
            
            const resPurch = await fetch(`${API_URL}/purchases/list`);
            purchasesList = (await resPurch.json()).files;
        } catch (e) { console.error("Error fetching lists"); }
    }

    function downloadFile(filename: string) {
        window.location.href = `${API_URL}/reports/download/${filename}`;
    }

    onMount(() => {
        fetchLiveStock();
        fetchLists();
        const interval = setInterval(() => {
            fetchLiveStock();
            fetchLists(); 
        }, 5000);
        return () => clearInterval(interval);
    });
</script>

<div class="min-h-screen bg-gray-50 pb-20 relative flex flex-col">
    
    <div class="bg-white shadow-sm border-b border-gray-200 px-6 py-4 flex justify-between items-center sticky top-0 z-20">
        <h1 class="text-2xl font-bold text-blue-800 tracking-tight">Sales Automation Manager</h1>
        
        <div class="group relative flex items-center gap-3 bg-blue-50 px-4 py-2 rounded-lg border border-blue-100 cursor-help transition-all hover:bg-blue-100 hover:shadow-md">
            
            <div class="text-right leading-tight">
                <p class="text-xs text-blue-500 font-bold uppercase tracking-wider">Current Stock</p>
                <p class="text-xl font-bold text-blue-900">{boxStock} <span class="text-sm font-normal text-blue-400">Boxes</span></p>
            </div>
            <div class="h-10 w-10 rounded-full bg-blue-200 flex items-center justify-center text-blue-700 font-bold text-lg">📦</div>

            <div class="absolute top-full right-0 mt-2 w-48 bg-gray-800 text-white text-sm rounded-lg shadow-xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 transform translate-y-2 group-hover:translate-y-0 z-50 p-3">
                <p class="font-bold text-gray-300 border-b border-gray-600 pb-1 mb-2 text-xs uppercase">Full Inventory</p>
                <div class="flex justify-between items-center mb-1">
                    <span>Soore Box:</span>
                    <span class="font-bold text-blue-300">{boxStock}</span>
                </div>
                <div class="flex justify-between items-center">
                    <span>Soore Liquid:</span>
                    <span class="font-bold text-green-300">{liquidStock}</span>
                </div>
            </div>

        </div>
    </div>

    <div class="max-w-5xl mx-auto w-full px-6 mt-8">
        
        <div class="flex justify-center gap-2 bg-gray-200 p-1 rounded-xl mb-8 w-fit mx-auto shadow-inner">
            <button 
                class="px-8 py-2 rounded-lg font-bold transition-all duration-200 cursor-pointer {mode === 'dashboard' ? 'bg-white text-blue-700 shadow-sm' : 'text-gray-500 hover:text-gray-700'}"
                on:click={() => mode='dashboard'}>
                Everyday Mode
            </button>
            <button 
                class="px-8 py-2 rounded-lg font-bold transition-all duration-200 cursor-pointer {mode === 'simulation' ? 'bg-white text-purple-700 shadow-sm' : 'text-gray-500 hover:text-gray-700'}"
                on:click={() => mode='simulation'}>
                History Backfill
            </button>
        </div>

        <div class="mb-12">
            {#if mode === 'dashboard'} <EverydayDashboard /> {/if}
            {#if mode === 'simulation'} <HistoryBackfill /> {/if}
        </div>

        <div class="bg-white rounded-xl shadow-lg border border-gray-200 overflow-hidden">
            <div class="bg-gray-50 px-6 py-4 border-b border-gray-200 flex justify-between items-center">
                <h3 class="font-bold text-xl text-gray-700 flex items-center gap-2">
                    📂 File History
                </h3>
                
                <div class="flex bg-gray-200 rounded-lg p-1 gap-1">
                    <button 
                        class="px-4 py-1 text-sm font-bold rounded-md transition-colors {sidebarTab==='sales' ? 'bg-white text-blue-700 shadow' : 'text-gray-500 hover:text-gray-700'}" 
                        on:click={() => sidebarTab='sales'}>
                        Sales Reports
                    </button>
                    <button 
                        class="px-4 py-1 text-sm font-bold rounded-md transition-colors {sidebarTab==='purchases' ? 'bg-white text-green-700 shadow' : 'text-gray-500 hover:text-gray-700'}" 
                        on:click={() => sidebarTab='purchases'}>
                        Purchase Logs
                    </button>
                </div>
            </div>

            <div class="p-6 bg-gray-50/50">
                {#if sidebarTab === 'sales'}
                    {#if reportsList.length === 0}
                        <div class="text-center py-8 text-gray-400 italic bg-white rounded-lg border border-dashed border-gray-300">No sales reports generated yet.</div>
                    {:else}
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {#each reportsList as file}
                                <div class="flex items-center gap-2 bg-white p-3 rounded-lg border border-gray-100 shadow-sm hover:shadow-md transition">
                                    <button 
                                        on:click={() => selectedReport = file}
                                        class="flex-1 text-left flex items-center gap-4 group cursor-pointer">
                                        <div class="h-10 w-10 rounded-full bg-blue-50 flex items-center justify-center text-xl group-hover:scale-110 transition">📊</div>
                                        <div class="overflow-hidden">
                                            <p class="font-bold text-gray-700 truncate">{file.replace('.xlsx', '')}</p>
                                            <p class="text-xs text-blue-500 font-semibold group-hover:underline">View Audit Log</p>
                                        </div>
                                    </button>
                                    
                                    <button 
                                        on:click={() => downloadFile(file)}
                                        class="h-10 w-10 flex items-center justify-center rounded-lg bg-gray-50 text-gray-400 hover:bg-green-100 hover:text-green-700 transition cursor-pointer"
                                        title="Download Excel">
                                        ⬇️
                                    </button>
                                </div>
                            {/each}
                        </div>
                    {/if}
                {/if}

                {#if sidebarTab === 'purchases'}
                    {#if purchasesList.length === 0}
                        <div class="text-center py-8 text-gray-400 italic bg-white rounded-lg border border-dashed border-gray-300">No purchase logs found.</div>
                    {:else}
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {#each purchasesList as file}
                                <button 
                                    on:click={() => selectedReport = file}
                                    class="text-left flex items-center gap-4 bg-white p-3 rounded-lg border border-gray-100 shadow-sm hover:shadow-md hover:border-green-200 transition group cursor-pointer">
                                    <div class="h-10 w-10 rounded-full bg-green-50 flex items-center justify-center text-xl group-hover:scale-110 transition">🚛</div>
                                    <div class="overflow-hidden">
                                        <p class="font-bold text-gray-700 truncate">{file.replace('_Purchases.json', '')}</p>
                                        <p class="text-xs text-green-600 font-semibold group-hover:underline">View Invoices</p>
                                    </div>
                                </button>
                            {/each}
                        </div>
                    {/if}
                {/if}
            </div>
        </div>
    </div>

    {#if selectedReport}
        <ReportViewer 
            filename={selectedReport} 
            onClose={() => selectedReport = null} 
        />
    {/if}
</div>