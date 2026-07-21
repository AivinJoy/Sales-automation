<!-- sales-ui\src\lib\components\HistoryBackfill.svelte -->

<script lang="ts">
    import { onMount } from 'svelte';
    import { API_URL } from '$lib/config';



    // Types matching the new Backend Model
    interface Product {
        id: number;
        name: string;
        rate: number;
    }

    interface InflowLineItem {
        product_id: number | null;
        qty: number | null;
        rate: number | null;   // defaults to the product's current rate, editable per line
    }

    interface InflowRow {
        date: string;
        invoice_no: string;
        items: InflowLineItem[];
    }

    // Converts DD/MM/YYYY -> YYYY-MM-DD (what <input type="date"> needs to display a value)
    function toISODate(dmy: string): string {
        if (!dmy) return "";
        const [d, m, y] = dmy.split("/");
        if (!d || !m || !y) return "";
        return `${y}-${m.padStart(2, '0')}-${d.padStart(2, '0')}`;
    }

    // Converts YYYY-MM-DD (native input's value) -> DD/MM/YYYY (what the backend expects)
    function toDMYDate(iso: string): string {
        if (!iso) return "";
        const [y, m, d] = iso.split("-");
        if (!d || !m || !y) return "";
        return `${d}/${m}/${y}`;
    }

    interface SimulationResult { 
        message: string; 
        file: string; 
        total_sales: number; 
        final_stock: string; 
    }
    
    let products: Product[] = []

    function currentRateFor(productId: number | null): number | null {
        const p = products.find(p => p.id === productId);
        return p ? p.rate : null;
    }

    // Form State
    let simMonth: number = 6;
    let simYear: number = 2025;
    let startingInvoice: number = 4520;
    
    // Dynamic opening stock: { [product_id]: qty }
    let openingStocks: Record<number, number> = {};

    // Stock inflow rows — one product per row now
    let stockInflows: InflowRow[] = [];

    // New Product form
    let newProductName = "";
    let newProductRate = 0;
    let addingProduct = false;

    // EDITABLE RATES (Default values, but user can change)
    let rateBox: number = 350;
    let rateLiquid: number = 280;
    
    let simResult: SimulationResult | null = null;
    let isLoading = false;

    async function fetchProducts() {
        try {
            const res = await fetch(`${API_URL}/products`);
            const data = await res.json();
            products = data.products || [];

            for (const p of products) {
                if (!(p.id in openingStocks)) openingStocks[p.id] = 0;
            }
            openingStocks = { ...openingStocks };

            if (stockInflows.length === 0 && products.length > 0) {
                stockInflows = [{ date: "", invoice_no: "INV-001", items: [{ product_id: products[0].id, qty: null, rate: currentRateFor(products[0].id) }] }];
            }
        } catch (e) {
            console.error("Could not fetch products", e);
        }
    }

    async function fetchLastState() {
        try {
            const res = await fetch(`${API_URL}/state`);
            const data = await res.json();
            startingInvoice = data.last_invoice + 1;

            const stockMap = data.stock_map || {};
            for (const p of products) {
                openingStocks[p.id] = stockMap[p.name] || 0;
            }
            openingStocks = { ...openingStocks };
        } catch (e) {
            console.error("Could not fetch state", e);
        }
    }

    onMount(async () => {
        await fetchProducts();
        await fetchLastState();
    });

    function nextInvoicePlaceholder(): string {
        return `INV-${String(stockInflows.length + 1).padStart(3, '0')}`;
    }

    function addInflowRow() {
        const defaultProduct = products.length > 0 ? products[0].id : null;
        stockInflows = [...stockInflows, { date: "", invoice_no: nextInvoicePlaceholder(), items: [{ product_id: defaultProduct, qty: null, rate: currentRateFor(defaultProduct) }] }];
    }

    function removeInflowRow(index: number) {
        stockInflows = stockInflows.filter((_, i) => i !== index);
    }

    function addLineItem(rowIndex: number) {
        const defaultProduct = products.length > 0 ? products[0].id : null;
        stockInflows[rowIndex].items = [...stockInflows[rowIndex].items, { product_id: defaultProduct, qty: null, rate: currentRateFor(defaultProduct) }];
    }

    function removeLineItem(rowIndex: number, itemIndex: number) {
        stockInflows[rowIndex].items = stockInflows[rowIndex].items.filter((_, i) => i !== itemIndex);
    }

    async function addNewProduct() {
        if (!newProductName.trim() || newProductRate <= 0) {
            alert("Enter a valid product name and rate.");
            return;
        }
        addingProduct = true;
        try {
            const res = await fetch(`${API_URL}/products`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: newProductName, rate: newProductRate })
            });
            if (!res.ok) throw new Error((await res.json()).detail || "Failed to add product");

            newProductName = "";
            newProductRate = 0;
            await fetchProducts();
        } catch (error) {
            alert("Error: " + (error as Error).message);
        } finally {
            addingProduct = false;
        }
    }

    async function updateProductRate(product: Product) {
        try {
            const res = await fetch(`${API_URL}/products/${product.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ rate: product.rate })
            });
            if (!res.ok) throw new Error("Failed to update rate");
        } catch (error) {
            alert("Error updating rate: " + (error as Error).message);
        }
    }

     async function runFullSimulation() {
        isLoading = true; simResult = null; 
        try {
            const payload = {
                month: simMonth, 
                year: simYear,
                opening_stocks: Object.entries(openingStocks).map(([product_id, opening_stock]) => ({
                    product_id: Number(product_id),
                    opening_stock
                })),
                starting_invoice: startingInvoice,
                stock_inflows: stockInflows
                    .filter(row => row.date)
                    .map(row => ({
                        date: row.date,
                        invoice_no: row.invoice_no,
                        inflows: row.items
                            .filter(item => item.product_id !== null && item.qty !== null && item.qty > 0)
                            .map(item => ({ product_id: item.product_id, qty: item.qty, rate: item.rate }))
                    }))
                    .filter(entry => entry.inflows.length > 0)
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

    <!-- PRODUCTS & RATES (replaces the old fixed Box/Liquid rate boxes + custom product section) -->
    <div class="mb-6 bg-blue-50 p-4 rounded-lg border border-blue-100">
        <p class="text-sm font-bold text-blue-800 mb-3">Products & Rates</p>
        <div class="space-y-2 mb-4">
            {#each products as product}
                <div class="flex items-center gap-3">
                    <span class="w-40 font-semibold text-blue-900 truncate">{product.name}</span>
                    <input 
                        type="number" 
                        bind:value={product.rate}
                        on:change={() => updateProductRate(product)}
                        class="w-32 p-2 border border-blue-300 rounded bg-white font-bold text-blue-900 focus:ring-2 focus:ring-blue-400 outline-none"
                    >
                    <span class="text-xs text-blue-400">₹ (editable, saved automatically)</span>
                </div>
            {/each}
        </div>

        <div class="flex items-end gap-3 pt-3 border-t border-blue-200">
            <div>
                <label for="newProductNameInput" class="block text-xs font-semibold mb-1 text-blue-700">New Product Name</label>
                <input id="newProductNameInput" type="text" bind:value={newProductName} placeholder="e.g. Soore Powder" class="p-2 border border-blue-300 rounded bg-white text-blue-900 focus:ring-2 focus:ring-blue-400 outline-none">
            </div>
            <div>
                <label for="newProductRateInput" class="block text-xs font-semibold mb-1 text-blue-700">Rate (₹)</label>
                <input id="newProductRateInput" type="number" bind:value={newProductRate} class="w-28 p-2 border border-blue-300 rounded bg-white text-blue-900 focus:ring-2 focus:ring-blue-400 outline-none">
            </div>
            <button 
                on:click={addNewProduct}
                disabled={addingProduct}
                class="cursor-pointer bg-blue-600 hover:bg-blue-700 text-white font-semibold px-4 py-2 rounded disabled:bg-gray-400">
                {addingProduct ? 'Adding...' : '+ New Product'}
            </button>
        </div>
    </div>

    <!-- OPENING STOCK (dynamic, one field per product) -->
    <p class="block text-sm font-semibold mb-2">Opening Stock</p>
    <div class="grid grid-cols-3 gap-6 mb-6">
        {#each products as product}
            <div>
                <label class="block text-sm font-semibold mb-1 text-gray-700">
                    {product.name}
                    <input type="number" bind:value={openingStocks[product.id]} class="mt-1 w-full p-2 border rounded focus:ring-2 focus:ring-gray-300 outline-none">
                </label>
            </div>
        {/each}
        <div>
            <label class="block text-sm font-semibold mb-1">
                Starting Invoice No.
                <span class="text-xs text-gray-400 font-normal">(Auto)</span>
                <input type="number" bind:value={startingInvoice} class="mt-1 w-full p-2 border-2 border-purple-100 rounded focus:ring-2 focus:ring-purple-300 outline-none font-bold text-gray-700">
            </label>
        </div>
    </div>

    <p class="block text-sm font-semibold mb-2">Stock Inflows (Purchases)</p>
    <div class="bg-gray-50 p-4 rounded-lg mb-6 border border-gray-200 space-y-4">
        {#each stockInflows as inflow, i}
            <div class="bg-white p-3 rounded-lg border border-gray-200">
                <div class="grid grid-cols-12 gap-2 mb-3 items-center">
                    <div class="col-span-5">
                        <label for={`inflowDate-${i}`} class="block text-xs font-bold text-gray-500 uppercase mb-1">Date</label>
                        <input 
                            id={`inflowDate-${i}`} 
                            type="date" 
                            value={toISODate(inflow.date)}
                            on:change={(e) => inflow.date = toDMYDate(e.currentTarget.value)}
                            class="w-full p-2 border rounded focus:ring-1 focus:ring-blue-300 outline-none"
                        >
                    </div>
                    <div class="col-span-5">
                        <label for={`inflowInvNo-${i}`} class="block text-xs font-bold text-gray-500 uppercase mb-1">Inv No</label>
                        <input id={`inflowInvNo-${i}`} type="text" bind:value={inflow.invoice_no} class="w-full p-2 border rounded focus:ring-1 focus:ring-blue-300 outline-none font-mono text-sm" placeholder="BILL-123">
                    </div>
                    <div class="col-span-2 text-right">
                        <button on:click={() => removeInflowRow(i)} class="text-red-500 hover:text-red-700 font-bold px-2 cursor-pointer" title="Remove Entire Bill" aria-label="Remove Bill">✕ Bill</button>
                    </div>
                </div>

                <div class="pl-2 border-l-2 border-blue-100 space-y-2">
                    {#each inflow.items as item, j}
                        <div class="grid grid-cols-12 gap-2 items-center">
                            <div class="col-span-4">
                                <select 
                                    bind:value={item.product_id} 
                                    on:change={() => item.rate = currentRateFor(item.product_id)}
                                    class="w-full p-2 border rounded focus:ring-1 focus:ring-blue-300 outline-none bg-white text-sm">
                                    {#each products as product}
                                        <option value={product.id}>{product.name}</option>
                                    {/each}
                                </select>
                            </div>
                            <div class="col-span-3">
                                <input type="number" aria-label="Qty" bind:value={item.qty} class="w-full p-2 border rounded focus:ring-1 focus:ring-blue-300 outline-none font-bold text-gray-700 text-center" placeholder="Qty">
                            </div>
                            <div class="col-span-3">
                                <input type="number" aria-label="Rate" bind:value={item.rate} class="w-full p-2 border rounded focus:ring-1 focus:ring-yellow-400 outline-none font-bold text-yellow-700 bg-yellow-50 text-center" placeholder="Rate ₹" title="Rate for this purchase — change only if this bill's price differs from the product's current rate">
                            </div>
                            <div class="col-span-2 text-center">
                                <button on:click={() => removeLineItem(i, j)} class="text-red-400 hover:text-red-600 font-bold px-2 cursor-pointer" title="Remove Product Line" aria-label="Remove Product Line">✕</button>
                            </div>
                        </div>
                    {/each}
                    <button on:click={() => addLineItem(i)} class="text-xs text-blue-600 font-semibold hover:underline cursor-pointer">+ Add Product to This Bill</button>
                </div>
            </div>
        {/each}
        
        <button on:click={addInflowRow} class="text-sm text-purple-600 font-semibold hover:underline mt-2 cursor-pointer">+ Add Another Purchase Bill</button>
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