// main.js - Coffee Shop Inventory Management System

document.addEventListener('DOMContentLoaded', function() {
    // Enable Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Enable Bootstrap popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto-close alerts after 5 seconds
    const autoCloseAlerts = document.querySelectorAll('.alert:not(.alert-danger):not(.alert-warning)');
    autoCloseAlerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
    
    // Initialize date inputs with current date if empty
    const dateInputs = document.querySelectorAll('input[type="date"]');
    dateInputs.forEach(function(input) {
        if (!input.value) {
            const today = new Date();
            const dateString = today.toISOString().split('T')[0];
            input.value = dateString;
        }
    });
    
    // Handle form submission with validation
    const forms = document.querySelectorAll('.needs-validation');
    Array.from(forms).forEach(function(form) {
        form.addEventListener('submit', function(event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
    
    // Handle inventory transaction form type selection
    const transactionTypeSelect = document.getElementById('transaction_type');
    if (transactionTypeSelect) {
        transactionTypeSelect.addEventListener('change', function() {
            const quantityInput = document.getElementById('quantity');
            const quantityLabel = document.querySelector('label[for="quantity"]');
            
            if (this.value === 'purchase') {
                quantityLabel.textContent = 'Quantity Added';
            } else if (this.value === 'usage') {
                quantityLabel.textContent = 'Quantity Used';
            } else if (this.value === 'adjustment') {
                quantityLabel.textContent = 'New Total Quantity';
            }
        });
    }
    
    // Search functionality enhancement
    const searchInput = document.getElementById('search');
    if (searchInput) {
        searchInput.addEventListener('keyup', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.closest('form').submit();
            }
        });
        
        // Focus search input when page loads if it exists
        searchInput.focus();
    }
});

// Format currency values
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD'
    }).format(value);
}

// Format date values
function formatDate(dateString) {
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    return new Date(dateString).toLocaleDateString('en-US', options);
}

// Convert table to CSV data
function tableToCSV(tableSelector) {
    const table = document.querySelector(tableSelector);
    if (!table) return null;
    
    let csv = [];
    const rows = table.querySelectorAll('tr');
    
    for (let i = 0; i < rows.length; i++) {
        const row = [], cols = rows[i].querySelectorAll('td, th');
        
        for (let j = 0; j < cols.length; j++) {
            // Get the text content and clean it
            let data = cols[j].textContent.replace(/\s+/g, ' ').trim();
            // Quote fields with commas
            if (data.includes(',')) {
                data = '"' + data + '"';
            }
            row.push(data);
        }
        
        csv.push(row.join(','));
    }
    
    return csv.join('\n');
}

// Download CSV function
function downloadCSV(csv, filename) {
    const csvFile = new Blob([csv], {type: 'text/csv'});
    const downloadLink = document.createElement('a');
    
    downloadLink.download = filename;
    downloadLink.href = window.URL.createObjectURL(csvFile);
    downloadLink.style.display = 'none';
    
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
}

// Export table data as CSV
function exportTableToCSV(tableSelector, filename) {
    const csv = tableToCSV(tableSelector);
    if (csv) {
        downloadCSV(csv, filename);
    }
}
