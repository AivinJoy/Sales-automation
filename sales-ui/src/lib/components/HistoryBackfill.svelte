<script lang="ts">
    import { onMount } from 'svelte';
    import { API_URL } from '$lib/config';

    // Types matching the new Backend Model
    interface StockEntry { 
        date: string; 
        invoice_no: string; 
        qty_box: number; 
        qty_liquid: number; 
    }
    
    interface SimulationResult { 
        message: string; 
        file: string; 
        total_sales: number; 
        final_stock: string; 
    }
    
    // Form State
    let simMonth: number = 6;
    let simYear: number = 2025;
    
    // Dual Opening Stock
    let openingStockBox: number = 0;
    let openingStockLiquid: number = 0;
    
    let startingInvoice: number = 4520;

    // EDITABLE RATES (Default values, but user can change)
    let rateBox: number = 350;
    let rateLiquid: number = 280;
    
    // Default Inflow Row (Dual Qty)
    let stockInflows: StockEntry[] = [{ 
        date: "05/06/2025", 
        invoice_no: "INV-001", 
        qty_box: 0, 
        qty_liquid: 0 
    }];
    
    let simResult: SimulationResult | null = null;
    let isLoading = false;

    async function fetchLastState() {
        try {
            const res = await fetch(`${API_URL}/state`);
            const data = await res.json();
            
            startingInvoice = data.last_invoice + 1;
            
            const stockMap = data.stock_map || {};
            openingStockBox = stockMap["Soore Box"] || 0;
            openingStockLiquid = stockMap["Soore Liquid"] || 0;
            
        } catch (e) { 
            console.error("Could not fetch state", e); 
        }
    }

    onMount(() => { fetchLastState(); });

    function addInflowRow() {
        stockInflows = [...stockInflows, { date: "", invoice_no: "", qty_box: 0, qty_liquid: 0 }];
    }

    function removeInflowRow(index: number) {
        stockInflows = stockInflows.filter((_, i) => i !== index);
    }

    async function runFullSimulation() {
        isLoading = true; simResult = null; 
        try {
            const payload = {
                month: simMonth, 
                year: simYear,
                opening_stock_box: openingStockBox,
                opening_stock_liquid: openingStockLiquid,
                starting_invoice: startingInvoice,
                // --- SEND USER-DEFINED RATES ---
                rate_box: rateBox,
                rate_liquid: rateLiquid,
                stock_inflows: stockInflows
            };
            
            const res = await fetch(`${API_URL}/simulate_month`, {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });
            
            if (!res.ok) throw new Error((await res.json()).detail || "Server Error");
            
            simResult = await res.json();
            await fetchLastState(); 
        } catch (error) { 
            alert("Error: " + (error as Error).message);
        } finally { 
            isLoading = false; 
        }
    }
    
    async function generateSummary(period: 'h1' | 'h2' | 'annual') {
         try {
            const res = await fetch(`${API_URL}/generate_summary`, {
                method: 'POST', headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ year: simYear, period: period })
            });
            const data = await res.json();
            if(data.success) alert(data.message); else alert("Error: " + data.message);
        } catch (error) { alert("Connection Error"); }
    }
</script>

<div class="bg-white p-8 rounded-xl shadow-lg border border-gray-100">
    <div class="flex justify-between items-center mb-6">
        <h3 class="text-2xl font-bold text-purple-700">Generate Past Month Report</h3>
        <button on:click={fetchLastState} class="text-xs bg-gray-100 hover:bg-gray-200 text-gray-600 px-2 py-1 rounded border cursor-pointer">🔄 Refresh Invoice #</button>
    </div>
    
    <div class="grid grid-cols-2 gap-6 mb-4">
        <div>
            <label class="block text-sm font-semibold mb-1">
                Month
                <input type="number" bind:value={simMonth} class="mt-1 w-full p-2 border rounded focus:ring-2 focus:ring-purple-200 outline-none" placeholder="1-12">
            </label>
        </div>
        <div>
            <label class="block text-sm font-semibold mb-1">
                Year
                <input type="number" bind:value={simYear} class="mt-1 w-full p-2 border rounded focus:ring-2 focus:ring-purple-200 outline-none">
            </label>
        </div>
    </div>

    <div class="grid grid-cols-2 gap-6 mb-4 bg-blue-50 p-3 rounded-lg border border-blue-100">
        <div>
            <label class="block text-sm font-semibold mb-1 text-blue-800">
                Rate: Soore Box (₹)
                <input type="number" bind:value={rateBox} class="mt-1 w-full p-2 border border-blue-300 rounded bg-white font-bold text-blue-900 shadow-sm focus:ring-2 focus:ring-blue-400 outline-none">
            </label>
        </div>
        <div>
            <label class="block text-sm font-semibold mb-1 text-blue-800">
                Rate: Soore Liquid (₹)
                <input type="number" bind:value={rateLiquid} class="mt-1 w-full p-2 border border-blue-300 rounded bg-white font-bold text-blue-900 shadow-sm focus:ring-2 focus:ring-blue-400 outline-none">
            </label>
        </div>
        <p class="col-span-2 text-xs text-blue-500 italic">You can edit these rates for this simulation.</p>
    </div>

    <div class="grid grid-cols-3 gap-6 mb-6">
        <div>
            <label class="block text-sm font-semibold mb-1 text-gray-700">
                Opening Stock (Box)
                <input type="number" bind:value={openingStockBox} class="mt-1 w-full p-2 border rounded focus:ring-2 focus:ring-gray-300 outline-none">
            </label>
        </div>
        <div>
            <label class="block text-sm font-semibold mb-1 text-gray-700">
                Opening Stock (Liquid)
                <input type="number" bind:value={openingStockLiquid} class="mt-1 w-full p-2 border rounded focus:ring-2 focus:ring-gray-300 outline-none">
            </label>
        </div>
        <div>
            <label class="block text-sm font-semibold mb-1">
                Starting Invoice No.
                <span class="text-xs text-gray-400 font-normal">(Auto)</span>
                <input type="number" bind:value={startingInvoice} class="mt-1 w-full p-2 border-2 border-purple-100 rounded focus:ring-2 focus:ring-purple-300 outline-none font-bold text-gray-700">
            </label>
        </div>
    </div>

    <p class="block text-sm font-semibold mb-2">Stock Inflows (Purchases)</p>
    <div class="bg-gray-50 p-4 rounded-lg mb-6 border border-gray-200">
        <div class="grid grid-cols-12 gap-2 mb-2 text-xs font-bold text-gray-500 uppercase text-center">
            <div class="col-span-3 text-left">Date</div>
            <div class="col-span-3 text-left">Inv No</div>
            <div class="col-span-2">Qty Box</div>
            <div class="col-span-2">Qty Liq</div>
            <div class="col-span-2"></div>
        </div>
        
        {#each stockInflows as inflow, i}
            <div class="grid grid-cols-12 gap-2 mb-2 items-center">
                <div class="col-span-3">
                    <input 
                        type="text" 
                        aria-label="Purchase Date" 
                        bind:value={inflow.date} 
                        class="w-full p-2 border rounded focus:ring-1 focus:ring-blue-300 outline-none" 
                        placeholder="DD/MM/YYYY"
                    >
                </div>
                <div class="col-span-3">
                    <input 
                        type="text" 
                        aria-label="Invoice Number" 
                        bind:value={inflow.invoice_no} 
                        class="w-full p-2 border rounded focus:ring-1 focus:ring-blue-300 outline-none font-mono text-sm" 
                        placeholder="BILL-123"
                    >
                </div>
                <div class="col-span-2">
                    <input 
                        type="number" 
                        aria-label="Qty Box" 
                        bind:value={inflow.qty_box} 
                        class="w-full p-2 border rounded focus:ring-1 focus:ring-blue-300 outline-none font-bold text-gray-700 text-center" 
                        placeholder="0"
                    >
                </div>
                <div class="col-span-2">
                    <input 
                        type="number" 
                        aria-label="Qty Liquid" 
                        bind:value={inflow.qty_liquid} 
                        class="w-full p-2 border rounded focus:ring-1 focus:ring-blue-300 outline-none font-bold text-gray-700 text-center" 
                        placeholder="0"
                    >
                </div>
                <div class="col-span-2 text-center">
                    <button 
                        on:click={() => removeInflowRow(i)} 
                        class="text-red-500 hover:text-red-700 font-bold px-2 cursor-pointer" 
                        title="Remove Entry"
                        aria-label="Remove Row"
                    >✕</button>
                </div>
            </div>
        {/each}
        
        <button on:click={addInflowRow} class="text-sm text-purple-600 font-semibold hover:underline mt-2 cursor-pointer">+ Add Another Purchase</button>
    </div>
    
    <hr class="my-6">
    
    <button 
        on:click={runFullSimulation}
        disabled={isLoading}
        class="w-full cursor-pointer text-white text-lg font-bold py-3 rounded-lg shadow-md transition-all 
        {isLoading ? 'bg-gray-400 cursor-not-allowed' : 'bg-purple-600 hover:bg-purple-700'}">
        {#if isLoading} ⏳ Generating... {:else} Generate Excel Report 📄 {/if}
    </button>

    {#if simResult}
        <div class="mt-6 p-6 bg-green-50 border border-green-200 rounded-lg text-green-900 shadow-sm animate-fade-in">
            <h4 class="text-xl font-bold mb-4">✅ Report Generated Successfully!</h4>
            
            <div class="grid grid-cols-2 gap-8 text-center">
                <div class="p-4 bg-white rounded-lg shadow-sm">
                    <p class="text-sm text-gray-500 uppercase font-semibold">Total Revenue</p>
                    <p class="text-2xl font-bold text-green-700">₹ {simResult.total_sales.toLocaleString()}</p>
                </div>
                <div class="p-4 bg-white rounded-lg shadow-sm border-2 border-green-500">
                    <p class="text-sm text-gray-500 uppercase font-semibold">Closing Balance</p>
                    <p class="text-lg font-bold text-gray-800">{simResult.final_stock}</p>
                </div>
            </div>

            <p class="mt-4 text-center text-gray-600 text-sm">
                File saved as: <code class="bg-gray-200 px-2 py-1 rounded font-bold">{simResult.file}</code>
            </p>
        </div>
    {/if}

    <div class="mt-8 pt-6 border-t border-gray-200">
        <h4 class="text-xl font-bold text-gray-700 mb-4">📂 Consolidated Reports</h4>
        <div class="grid grid-cols-3 gap-4">
            <button on:click={() => generateSummary('h1')} class="cursor-pointer bg-indigo-100 hover:bg-indigo-200 text-indigo-800 font-semibold py-2 px-4 rounded transition-colors">Download H1 (Jan-Jun)</button>
            <button on:click={() => generateSummary('h2')} class="cursor-pointer bg-indigo-100 hover:bg-indigo-200 text-indigo-800 font-semibold py-2 px-4 rounded transition-colors">Download H2 (Jul-Dec)</button>
            <button on:click={() => generateSummary('annual')} class="cursor-pointer bg-gray-800 hover:bg-black text-white font-semibold py-2 px-4 rounded transition-colors">Download Annual Report</button>
        </div>
    </div>
</div>