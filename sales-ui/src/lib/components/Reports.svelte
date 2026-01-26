<script lang="ts">
    import { API_URL } from '$lib/config';
    export let filename: string;
    export let onClose: () => void;

    let reportData: any[] = [];
    let loading = true;
    let error = "";
    let viewType = "excel"; // 'excel', 'audit', or 'purchase'

    async function loadReport() {
        try {
            // Determine URL based on filename extension
            let url = `${API_URL}/reports/view/${filename}`;
            if (filename.endsWith("_Purchases.json")) {
                url = `${API_URL}/purchases/view/${filename}`;
            }

            const res = await fetch(url);
            const json = await res.json();
            
            if (!res.ok) throw new Error(json.detail || "Failed to load");
            
            reportData = json.data;
            viewType = json.type; 
        } catch (e) {
            error = (e as Error).message;
        } finally {
            loading = false;
        }
    }

    loadReport();

    // Helper to color rows based on Type or Content
    function getRowColor(row: any) {
        // 1. Highlight Total Row in Purchase Logs
        if (row["Date"] === "TOTAL") return "bg-gray-800 text-white font-bold";

        // 2. Audit Log Coloring (Holiday, Quiet, Stock)
        const type = row["Type"];
        if (type) {
            if (type.includes("Holiday") || type.includes("Quiet")) return "bg-red-50 text-red-600 italic";
            if (type.includes("Stock Added")) return "bg-green-100 text-green-800 font-bold";
        }
        
        return "bg-white";
    }
</script>

<div class="fixed inset-0 bg-black/60 flex justify-center items-center z-50 p-6 backdrop-blur-sm">
    <div class="bg-white rounded-xl shadow-2xl w-full max-w-5xl h-[85vh] flex flex-col overflow-hidden animate-fade-in">
        
        <div class="p-4 border-b flex justify-between items-center bg-gray-50">
            <div>
                <h3 class="text-xl font-bold text-gray-700">📄 {filename.replace('_Purchases.json', '')}</h3>
                
                {#if viewType === 'audit'}
                    <span class="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded-full font-bold">Detailed Audit Log</span>
                {/if}
                {#if viewType === 'purchase'}
                    <span class="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full font-bold">Purchase / Inflow Log</span>
                {/if}
            </div>
            <button on:click={onClose} class="cursor-pointer text-gray-500 hover:text-red-600 font-bold text-xl px-2">✕</button>
        </div>

        <div class="flex-1 overflow-auto p-4">
            {#if loading}
                <div class="flex justify-center items-center h-full text-gray-500 text-lg">⏳ Loading data...</div>
            {:else if error}
                <div class="text-red-600 text-center font-bold mt-10">⚠️ Error: {error}</div>
            {:else if reportData.length === 0}
                <div class="text-center text-gray-500 mt-10">This file is empty.</div>
            {:else}
                <table class="w-full text-sm text-left border-collapse">
                    <thead class="bg-blue-100 text-blue-800 sticky top-0 shadow-sm">
                        <tr>
                            {#each Object.keys(reportData[0]) as header}
                                {#if !header.startsWith('_')}
                                    <th class="p-3 border-b border-blue-200 font-bold whitespace-nowrap">{header}</th>
                                {/if}
                            {/each}
                        </tr>
                    </thead>
                    <tbody>
                        {#each reportData as row}
                            <tr class="border-b border-gray-100 hover:bg-gray-50 {getRowColor(row)}">
                                {#each Object.entries(row) as [key, val]}
                                    {#if !key.startsWith('_')}
                                        <td class="p-3 truncate max-w-50" title={String(val)}>{val}</td>
                                    {/if}
                                {/each}
                            </tr>
                        {/each}
                    </tbody>
                </table>
            {/if}
        </div>

        <div class="p-3 bg-gray-50 border-t text-right">
            <button on:click={onClose} class="cursor-pointer bg-gray-800 text-white px-6 py-2 rounded hover:bg-black transition">Close</button>
        </div>
    </div>
</div>