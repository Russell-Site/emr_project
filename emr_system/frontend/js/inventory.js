// ============================================================
// INVENTORY MODULE
// ============================================================

let inventoryItems = [];
let filteredInventoryItems = [];


// ============================================================
// LOAD INVENTORY
// ============================================================

async function loadInventory() {
    try {
        const response = await fetch("/api/inventory");

        if (!response.ok) {
            throw new Error("Failed to load inventory.");
        }

        inventoryItems = await response.json();

        filterInventory();

    } catch (error) {
        console.error("Inventory loading error:", error);

        const tbody = document.getElementById("inventoryTableBody");

        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="7" style="text-align:center;">
                        Failed to load inventory.
                    </td>
                </tr>
            `;
        }
    }
}


// ============================================================
// RENDER INVENTORY
// ============================================================

function renderInventory() {
    const tbody = document.getElementById("inventoryTableBody");

    if (!tbody) return;

    if (filteredInventoryItems.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" style="text-align:center;">
                    No inventory items found.
                </td>
            </tr>
        `;
        return;
    }

    tbody.innerHTML = filteredInventoryItems.map(item => {

        const quantity = Number(item.quantity || 0);
        const reorderLevel = Number(item.reorder_level || 0);

        let status = "In Stock";
        let statusClass = "badge-active";

        if (quantity === 0) {
            status = "Out of Stock";
            statusClass = "badge-locked";
        } else if (quantity <= reorderLevel) {
            status = "Low Stock";
            statusClass = "badge-inactive";
        }

        return `
            <tr>

                <td>
                    <strong>
                        ${escapeInventoryHTML(item.item_name)}
                    </strong>

                    ${
                        item.description
                            ? `
                                <br>
                                <small style="color:var(--muted);">
                                    ${escapeInventoryHTML(item.description)}
                                </small>
                              `
                            : ""
                    }
                </td>

                <td>
                    ${escapeInventoryHTML(item.category)}
                </td>

                <td>
                    ${escapeInventoryHTML(item.unit)}
                </td>

                <td>
                    <strong>${quantity}</strong>
                </td>

                <td>
                    ${reorderLevel}
                </td>

                <td>
                    <span class="badge ${statusClass}">
                        ${status}
                    </span>
                </td>

                <td>
                    <div style="
                        display:flex;
                        gap:6px;
                        flex-wrap:wrap;
                    ">

                        <button
                            type="button"
                            class="btn btn-primary btn-sm"
                            onclick="openStockModal(${item.item_id})"
                        >
                            Stock
                        </button>

                        <button
                            type="button"
                            class="btn btn-outline btn-sm"
                            onclick="editInventoryItem(${item.item_id})"
                        >
                            Edit
                        </button>

                        <button
                            type="button"
                            class="btn btn-outline btn-sm"
                            onclick="deleteInventoryItem(${item.item_id})"
                        >
                            Delete
                        </button>

                    </div>
                </td>

            </tr>
        `;

    }).join("");
}


// ============================================================
// STATISTICS
// ============================================================

function updateInventoryStats() {

    const totalItems = inventoryItems.length;

    const medicineCount = inventoryItems.filter(
        item => item.category === "Medicine"
    ).length;

    const vaccineCount = inventoryItems.filter(
        item => item.category === "Vaccine"
    ).length;

    const supplyCount = inventoryItems.filter(
        item => item.category === "Medical Supply"
    ).length;

    const lowStockCount = inventoryItems.filter(item => {

        const quantity = Number(item.quantity || 0);
        const reorderLevel = Number(item.reorder_level || 0);

        return quantity > 0 && quantity <= reorderLevel;

    }).length;

    const outOfStockCount = inventoryItems.filter(item => {
        return Number(item.quantity || 0) === 0;
    }).length;


    setInventoryText("inventoryTotalItems", totalItems);
    setInventoryText("inventoryMedicineCount", medicineCount);
    setInventoryText("inventoryVaccineCount", vaccineCount);
    setInventoryText("inventorySupplyCount", supplyCount);
    setInventoryText("inventoryLowStockCount", lowStockCount);
    setInventoryText("inventoryOutOfStockCount", outOfStockCount);
}


function setInventoryText(id, value) {

    const element = document.getElementById(id);

    if (element) {
        element.textContent = value;
    }
}


// ============================================================
// SEARCH + FILTER
// ============================================================

function filterInventory() {

    const searchInput =
        document.getElementById("inventorySearch");

    const categoryFilter =
        document.getElementById("inventoryCategoryFilter");

    const statusFilter =
        document.getElementById("inventoryStatusFilter");


    const search = searchInput
        ? searchInput.value.toLowerCase().trim()
        : "";

    const category = categoryFilter
        ? categoryFilter.value
        : "";

    const status = statusFilter
        ? statusFilter.value
        : "";


    filteredInventoryItems = inventoryItems.filter(item => {

        const itemName = String(
            item.item_name || ""
        ).toLowerCase();

        const itemCategory = String(
            item.category || ""
        );

        const quantity = Number(
            item.quantity || 0
        );

        const reorderLevel = Number(
            item.reorder_level || 0
        );


        let itemStatus = "In Stock";

        if (quantity === 0) {
            itemStatus = "Out of Stock";
        } else if (quantity <= reorderLevel) {
            itemStatus = "Low Stock";
        }


        const matchesSearch =
            !search ||
            itemName.includes(search);

        const matchesCategory =
            !category ||
            itemCategory === category;

        const matchesStatus =
            !status ||
            itemStatus === status;


        return (
            matchesSearch &&
            matchesCategory &&
            matchesStatus
        );

    });


    renderInventory();
    updateInventoryStats();
}


// ============================================================
// OPEN ADD INVENTORY MODAL
// ============================================================

function openInventoryModal() {

    const modal =
        document.getElementById("inventoryModal");

    const form =
        document.getElementById("inventoryForm");


    if (!modal || !form) {
        console.error("Inventory modal not found.");
        return;
    }


    form.reset();


    const editId =
        document.getElementById("inventoryEditId");

    const title =
        document.getElementById("inventoryModalTitle");

    const submitButton =
        document.getElementById("inventorySubmitButton");

    const reorderLevel =
        document.getElementById("inventoryReorderLevel");

    const initialQuantity =
        document.getElementById("inventoryInitialQuantity");

    const initialQuantityGroup =
        document.getElementById(
            "inventoryInitialQuantityGroup"
        );


    if (editId) editId.value = "";

    if (title) {
        title.textContent = "Add Inventory Item";
    }

    if (submitButton) {
        submitButton.textContent = "Add Item";
    }

    if (reorderLevel) {
        reorderLevel.value = 10;
    }

    if (initialQuantity) {
        initialQuantity.value = 0;
    }

    if (initialQuantityGroup) {
        initialQuantityGroup.style.display = "block";
    }


    modal.classList.add("show");
}


// ============================================================
// CLOSE INVENTORY MODAL
// ============================================================

function closeInventoryModal() {

    const modal =
        document.getElementById("inventoryModal");

    if (modal) {
        modal.classList.remove("show");
    }
}


// ============================================================
// EDIT INVENTORY ITEM
// ============================================================

function editInventoryItem(itemId) {

    const item = inventoryItems.find(
        item => Number(item.item_id) === Number(itemId)
    );


    if (!item) {
        alert("Inventory item not found.");
        return;
    }


    const modal =
        document.getElementById("inventoryModal");


    if (!modal) {
        console.error("Inventory modal not found.");
        return;
    }


    document.getElementById(
        "inventoryEditId"
    ).value = item.item_id;


    document.getElementById(
        "inventoryItemName"
    ).value = item.item_name || "";


    document.getElementById(
        "inventoryCategory"
    ).value = item.category || "";


    document.getElementById(
        "inventoryUnit"
    ).value = item.unit || "";


    document.getElementById(
        "inventoryReorderLevel"
    ).value = item.reorder_level ?? 10;


    document.getElementById(
        "inventoryDescription"
    ).value = item.description || "";


    document.getElementById(
        "inventoryModalTitle"
    ).textContent = "Edit Inventory Item";


    document.getElementById(
        "inventorySubmitButton"
    ).textContent = "Save Changes";


    document.getElementById(
        "inventoryInitialQuantityGroup"
    ).style.display = "none";


    modal.classList.add("show");
}


// ============================================================
// INVENTORY FORM SUBMIT
// ============================================================

function setupInventoryForm() {

    const form =
        document.getElementById("inventoryForm");

    if (!form) return;


    form.addEventListener("submit", async function(event) {

        event.preventDefault();


        const currentUser =
            typeof getCurrentUser === "function"
                ? getCurrentUser()
                : null;


        if (!currentUser || !currentUser.user_id) {

            alert(
                "User session not found. Please log in again."
            );

            return;
        }


        const editId = Number(
            document.getElementById(
                "inventoryEditId"
            ).value || 0
        );


        const itemName =
            document.getElementById(
                "inventoryItemName"
            ).value.trim();


        const category =
            document.getElementById(
                "inventoryCategory"
            ).value;


        const unit =
            document.getElementById(
                "inventoryUnit"
            ).value.trim();


        const reorderLevel =
            Number(
                document.getElementById(
                    "inventoryReorderLevel"
                ).value
            );


        const initialQuantity =
            Number(
                document.getElementById(
                    "inventoryInitialQuantity"
                ).value
            );


        const description =
            document.getElementById(
                "inventoryDescription"
            ).value.trim();


        if (!itemName) {
            alert("Please enter the item name.");
            return;
        }


        if (!category) {
            alert("Please select a category.");
            return;
        }


        if (!unit) {
            alert("Please enter the unit.");
            return;
        }


        if (
            reorderLevel < 0 ||
            initialQuantity < 0
        ) {
            alert(
                "Quantity and reorder level cannot be negative."
            );
            return;
        }


        const submitButton =
            document.getElementById(
                "inventorySubmitButton"
            );


        if (submitButton) {
            submitButton.disabled = true;

            submitButton.textContent =
                editId > 0
                    ? "Saving..."
                    : "Adding...";
        }


        try {

            let response;


            // ====================================================
            // EDIT
            // ====================================================

            if (editId > 0) {

                response = await fetch(
                    `/api/inventory/${editId}`,
                    {
                        method: "PUT",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({

                            item_name:
                                itemName,

                            category:
                                category,

                            unit:
                                unit,

                            reorder_level:
                                reorderLevel,

                            description:
                                description,

                            user_id:
                                Number(
                                    currentUser.user_id
                                )

                        })
                    }
                );


            // ====================================================
            // ADD
            // ====================================================

            } else {

                response = await fetch(
                    "/api/inventory",
                    {
                        method: "POST",

                        headers: {
                            "Content-Type":
                                "application/json"
                        },

                        body: JSON.stringify({

                            item_name:
                                itemName,

                            category:
                                category,

                            unit:
                                unit,

                            reorder_level:
                                reorderLevel,

                            quantity:
                                initialQuantity,

                            description:
                                description,

                            user_id:
                                Number(
                                    currentUser.user_id
                                )

                        })
                    }
                );
            }


            const data = await response.json();


            if (!response.ok) {

                throw new Error(
                    data.detail ||
                    "Inventory request failed."
                );
            }


            alert(
                editId > 0
                    ? "Inventory item updated successfully."
                    : "Inventory item added successfully."
            );


            closeInventoryModal();

            await loadInventory();


        } catch (error) {

            console.error(
                "Inventory form error:",
                error
            );


            alert(
                error.message ||
                "Failed to save inventory item."
            );


        } finally {

            if (submitButton) {

                submitButton.disabled = false;

                submitButton.textContent =
                    editId > 0
                        ? "Save Changes"
                        : "Add Item";
            }
        }

    });
}


// ============================================================
// OPEN STOCK MODAL
// ============================================================

function openStockModal(itemId) {

    const item = inventoryItems.find(
        item => Number(item.item_id) === Number(itemId)
    );


    if (!item) {
        alert("Inventory item not found.");
        return;
    }


    const modal =
        document.getElementById("stockModal");


    if (!modal) {
        console.error("Stock modal not found.");
        return;
    }


    const stockForm =
        document.getElementById("stockForm");


    if (stockForm) {
        stockForm.reset();
    }


    const stockItemId =
        document.getElementById("stockItemId");

    const stockItemName =
        document.getElementById("stockItemName");

    const stockCurrentQuantity =
        document.getElementById(
            "stockCurrentQuantity"
        );

    const stockTransactionType =
        document.getElementById(
            "stockTransactionType"
        );

    const stockQuantity =
        document.getElementById("stockQuantity");

    const stockRemarks =
        document.getElementById("stockRemarks");

    const stockModalTitle =
        document.getElementById("stockModalTitle");

    const stockSubmitButton =
        document.getElementById(
            "stockSubmitButton"
        );


    if (stockItemId) {
        stockItemId.value = item.item_id;
    }

    if (stockItemName) {
        stockItemName.value = item.item_name || "";
    }

    if (stockCurrentQuantity) {
        stockCurrentQuantity.value =
            Number(item.quantity || 0);
    }

    if (stockTransactionType) {
        stockTransactionType.value = "Stock In";
    }

    if (stockQuantity) {
        stockQuantity.value = 1;
    }

    if (stockRemarks) {
        stockRemarks.value = "";
    }

    if (stockModalTitle) {
        stockModalTitle.textContent =
            "Update Stock";
    }

    if (stockSubmitButton) {
        stockSubmitButton.textContent =
            "Save Stock";
    }


    modal.classList.add("show");
}


// ============================================================
// CLOSE STOCK MODAL
// ============================================================

function closeStockModal() {

    const modal =
        document.getElementById("stockModal");

    if (modal) {
        modal.classList.remove("show");
    }
}


// ============================================================
// STOCK FORM SUBMIT
// ============================================================

function setupStockForm() {

    const stockForm =
        document.getElementById("stockForm");

    if (!stockForm) return;


    stockForm.addEventListener("submit", async function(event) {

        event.preventDefault();


        const currentUser =
            typeof getCurrentUser === "function"
                ? getCurrentUser()
                : null;


        if (!currentUser || !currentUser.user_id) {

            alert(
                "User session not found. Please log in again."
            );

            return;
        }


        const itemId = Number(
            document.getElementById(
                "stockItemId"
            ).value
        );


        const transactionType =
            document.getElementById(
                "stockTransactionType"
            ).value;


        const quantity =
            Number(
                document.getElementById(
                    "stockQuantity"
                ).value
            );


        const remarks =
            document.getElementById(
                "stockRemarks"
            ).value.trim();


        if (!itemId) {
            alert("Inventory item not found.");
            return;
        }


        if (!quantity || quantity <= 0) {

            alert(
                "Quantity must be greater than 0."
            );

            return;
        }


        const submitButton =
            document.getElementById(
                "stockSubmitButton"
            );


        if (submitButton) {

            submitButton.disabled = true;
            submitButton.textContent = "Saving...";
        }


        try {

            const endpoint =
                transactionType === "Stock In"
                    ? `/api/inventory/${itemId}/stock-in`
                    : `/api/inventory/${itemId}/stock-out`;


            const response = await fetch(
                endpoint,
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json"
                    },

                    body: JSON.stringify({

                        quantity:
                            quantity,

                        remarks:
                            remarks,

                        user_id:
                            Number(
                                currentUser.user_id
                            )

                    })
                }
            );


            const data = await response.json();


            if (!response.ok) {

                throw new Error(
                    data.detail ||
                    "Failed to update stock."
                );
            }


            alert(
                transactionType === "Stock In"
                    ? "Stock added successfully."
                    : "Stock removed successfully."
            );


            closeStockModal();

            await loadInventory();


        } catch (error) {

            console.error(
                "Stock transaction error:",
                error
            );


            alert(
                error.message ||
                "Failed to update stock."
            );


        } finally {

            if (submitButton) {

                submitButton.disabled = false;
                submitButton.textContent =
                    "Save Stock";
            }
        }

    });
}


// ============================================================
// DELETE INVENTORY ITEM
// ============================================================

async function deleteInventoryItem(itemId) {

    const item = inventoryItems.find(
        item => Number(item.item_id) === Number(itemId)
    );


    if (!item) {
        alert("Inventory item not found.");
        return;
    }


    const confirmed = confirm(
        `Are you sure you want to delete "${item.item_name}"?`
    );


    if (!confirmed) return;


    try {

        const response = await fetch(
            `/api/inventory/${itemId}`,
            {
                method: "DELETE"
            }
        );


        const data =
            await response.json().catch(() => ({}));


        if (!response.ok) {

            throw new Error(
                data.detail ||
                "Failed to delete inventory item."
            );
        }


        alert(
            "Inventory item deleted successfully."
        );


        await loadInventory();


    } catch (error) {

        console.error(
            "Delete inventory error:",
            error
        );


        alert(
            error.message ||
            "Failed to delete inventory item."
        );
    }
}


// ============================================================
// WEBSOCKET INVENTORY HANDLER
// ============================================================

function handleInventoryWebSocketMessage(data) {

    console.log(
        "📦 Inventory WebSocket message:",
        data
    );


    if (
        data.type === "inventory_created" ||
        data.type === "inventory_updated" ||
        data.type === "inventory_deleted" ||
        data.type === "inventory_stock_updated"
    ) {

        console.log(
            "🔄 Inventory changed — refreshing automatically..."
        );


        loadInventory();
    }
}


// ============================================================
// HTML ESCAPE
// ============================================================

function escapeInventoryHTML(value) {

    return String(value ?? "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


// ============================================================
// MODAL BACKDROP CLICK
// ============================================================

function setupInventoryModalEvents() {

    const inventoryModal =
        document.getElementById("inventoryModal");

    const stockModal =
        document.getElementById("stockModal");


    if (inventoryModal) {

        inventoryModal.addEventListener(
            "click",
            function(event) {

                if (event.target === inventoryModal) {
                    closeInventoryModal();
                }

            }
        );
    }


    if (stockModal) {

        stockModal.addEventListener(
            "click",
            function(event) {

                if (event.target === stockModal) {
                    closeStockModal();
                }

            }
        );
    }


    // ESC key closes modals
    document.addEventListener(
        "keydown",
        function(event) {

            if (event.key !== "Escape") return;

            closeInventoryModal();
            closeStockModal();

        }
    );
}


// ============================================================
// INITIALIZE INVENTORY
// ============================================================

document.addEventListener(
    "DOMContentLoaded",
    function() {

        loadInventory();

        setupInventoryForm();

        setupStockForm();

        setupInventoryModalEvents();


        const searchInput =
            document.getElementById(
                "inventorySearch"
            );


        const categoryFilter =
            document.getElementById(
                "inventoryCategoryFilter"
            );


        const statusFilter =
            document.getElementById(
                "inventoryStatusFilter"
            );


        if (searchInput) {

            searchInput.addEventListener(
                "input",
                filterInventory
            );
        }


        if (categoryFilter) {

            categoryFilter.addEventListener(
                "change",
                filterInventory
            );
        }


        if (statusFilter) {

            statusFilter.addEventListener(
                "change",
                filterInventory
            );
        }

    }
);