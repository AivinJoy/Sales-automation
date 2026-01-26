<script lang="ts">
    import { onMount } from 'svelte';
    import { API_URL } from '$lib/config';

    // State Variables
    let stockMap: Record<string, number> = {};
    let totalSalesVal = 0;
    
    // Product Selector
    const products = ["Soore Box", "Soore Liquid"];
    let selectedProduct = products[0]; // Default to Box

    // Action Form
    let addQty = 0;
    let isProcessing = false;
    let statusMsg = "";

    // Derived State: Automatically updates when stockMap or selectedProduct changes
    $: currentStock = stockMap[selectedProduct] || 0;

    async function fetchState() {
        try {
            const res = await fetch(`${API_URL}/state`);
            const data = await res.json();
            
            // Save the full map (e.g., { "Soore Box": 25, "Soore Liquid": 100 })
            stockMap = data.stock_map || {};
            totalSalesVal = data.total_sales_val || 0;
            
        } catch (e) { 
            console.error("Backend Offline?", e); 
        } 
    }

    onMount(() => { fetchState(); });

    async function performAction(action: 'add_stock' | 'simulate') {
        if (action === 'add_stock' && addQty <= 0) {
            alert("Please enter a valid quantity.");
            return;
        }

        isProcessing = true; 
        statusMsg = "";
        
        try {
            const payload = {
                action: action,
                qty: addQty,
                product_name: selectedProduct // <--- Send Selected Product
            };

            const res = await fetch(`${API_URL}/everyday/action`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(payload)
            });

            const data = await res.json();
            
            if (action === 'add_stock') {
                statusMsg = `✅ Added ${addQty} to ${selectedProduct}`;
                addQty = 0; // Reset input
            } else {
                statusMsg = `✅ ${data.message}`;
            }

            // Refresh Data to see new stock/sales
            await fetchState();

        } catch (error) {
            statusMsg = "❌ Error: Connection Failed";
        } finally {
            isProcessing = false;
        }
    }
</script>

<div class="flex justify-between items-center mb-6">
    <h2 class="text-2xl font-bold text-gray-800">Live Dashboard</h2>
    
    <div class="relative">
        <select 
            bind:value={selectedProduct}
            class="appearance-none bg-indigo-50 border border-indigo-200 text-indigo-700 py-2 pl-4 pr-8 rounded-lg font-semibold cursor-pointer focus:ring-2 focus:ring-indigo-300 outline-none hover:bg-indigo-100 transition-colors"
        >
            {#each products as p}
                <option value={p}>{p}</option>
            {/each}
        </select>
        <div class="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-indigo-700">
            <svg class="fill-current h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20"><path d="M9.293 12.95l.707.707L15.657 8l-1.414-1.414L10 10.828 5.757 6.586 4.343 8z"/></svg>
        </div>
    </div>
</div>

<div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
    <div class="bg-white p-6 rounded-xl shadow-md border-l-4 border-blue-500 transition-all">
        <h3 class="text-lg font-semibold text-gray-500 uppercase">Current Stock</h3>
        <p class="text-sm text-gray-400 mb-2">for {selectedProduct}</p>
        
        <div class="flex items-baseline gap-2">
            <div class="text-4xl font-bold text-gray-800">{currentStock}</div>
            <span class="text-lg font-normal text-gray-400">Boxes</span>
        </div>
        
        <div class="mt-2 text-sm bg-blue-50 text-blue-800 inline-block px-2 py-1 rounded">
            Target Buffer: 20-50
        </div>
    </div>
    
    <div class="bg-white p-6 rounded-xl shadow-md border-l-4 border-green-500">
        <h3 class="text-lg font-semibold text-gray-500 uppercase">Total Sales (All Products)</h3>
        <p class="text-sm text-gray-400 mb-2">Year to Date</p>
        <div class="text-4xl font-bold my-2 text-green-700">₹ {totalSalesVal.toLocaleString()}</div>
    </div>
</div>

<div class="bg-gray-50 p-6 rounded-xl shadow-inner border border-gray-200">
    <h3 class="text-xl font-bold mb-4 text-gray-700">Quick Actions for <span class="text-indigo-600">{selectedProduct}</span></h3>
    
    <div class="flex flex-col md:flex-row gap-6 items-end">
        
        <button 
            on:click={() => performAction('simulate')}
            disabled={isProcessing}
            class="flex-1 w-full md:w-auto cursor-pointer bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-medium shadow transition-all disabled:bg-gray-400 disabled:cursor-not-allowed">
            {isProcessing ? '⏳ Processing...' : "⚡ Run Today's Sales"}
        </button>

        <div class="flex-1 w-full md:w-auto flex gap-2 items-center bg-white p-2 rounded-lg border border-gray-300">
            <input 
                type="number" 
                bind:value={addQty} 
                placeholder="Qty" 
                class="w-24 p-2 border-none outline-none font-bold text-gray-700 bg-transparent text-center"
            >
            <button 
                on:click={() => performAction('add_stock')}
                disabled={isProcessing}
                class="grow cursor-pointer bg-gray-700 hover:bg-gray-800 text-white px-4 py-2 rounded-md font-medium shadow transition-all disabled:bg-gray-400">
                + Add Stock
            </button>
        </div>
        
    </div>

    {#if statusMsg}
        <div class="mt-4 p-3 bg-white border border-gray-200 rounded text-sm font-semibold text-gray-700 animate-fade-in">
            {statusMsg}
        </div>
    {/if}
</div>