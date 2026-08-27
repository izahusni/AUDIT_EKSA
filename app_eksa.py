<!DOCTYPE html>
<html lang="ms">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Borang Pendaftaran | Cikgu Zam</title>
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- FontAwesome -->
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        body { font-family: 'Inter', sans-serif; }
        /* Custom checkbox styling for Google Forms look */
        .custom-checkbox:checked + div {
            background-color: #f3e8ff; /* purple-100 */
            border-color: #9333ea; /* purple-600 */
        }
    </style>
</head>
<body class="bg-indigo-50 min-h-screen py-10">

    <!-- Navigasi Kembali -->
    <div class="max-w-3xl mx-auto px-4 mb-6">
        <a href="index.html" class="text-indigo-600 hover:text-indigo-800 font-medium flex items-center transition">
            <i class="fa-solid fa-arrow-left mr-2"></i> Kembali ke Laman Utama
        </a>
    </div>

    <!-- Container Borang -->
    <div class="max-w-3xl mx-auto px-4">
        <form onsubmit="event.preventDefault(); alert('Pendaftaran berjaya dihantar! Kami akan hubungi anda sebentar lagi.');">
            
            <!-- Header Borang -->
            <div class="bg-white rounded-lg shadow-md mb-6 overflow-hidden border border-gray-200">
                <div class="h-3 bg-purple-600 w-full"></div>
                <div class="p-8">
                    <h1 class="text-4xl font-bold text-gray-900 mb-2">REGISTRATION FORM</h1>
                    <p class="text-sm font-bold text-gray-700 tracking-wide">PERSONAL COACHING WITH CIKGU ZAM</p>
                </div>
            </div>

            <!-- Maklumat Peribadi -->
            <div class="bg-white rounded-lg shadow-md mb-6 p-8 border border-gray-200">
                <h2 class="text-xl font-semibold mb-6 border-b pb-2">Maklumat Peserta</h2>
                
                <div class="mb-6">
                    <label class="block text-base font-medium text-gray-800 mb-2">Nama Penuh <span class="text-red-500">*</span></label>
                    <input type="text" class="w-full md:w-2/3 border-b-2 border-gray-300 focus:border-purple-600 focus:outline-none py-2 text-gray-700 transition" placeholder="Jawapan anda" required>
                </div>

                <div class="mb-6">
                    <label class="block text-base font-medium text-gray-800 mb-2">Nombor Telefon (WhatsApp) <span class="text-red-500">*</span></label>
                    <input type="tel" class="w-full md:w-2/3 border-b-2 border-gray-300 focus:border-purple-600 focus:outline-none py-2 text-gray-700 transition" placeholder="Jawapan anda" required>
                </div>

                <div class="mb-2">
                    <label class="block text-base font-medium text-gray-800 mb-2">E-mel <span class="text-red-500">*</span></label>
                    <input type="email" class="w-full md:w-2/3 border-b-2 border-gray-300 focus:border-purple-600 focus:outline-none py-2 text-gray-700 transition" placeholder="Jawapan anda" required>
                </div>
            </div>

            <!-- Senarai Kursus (Merujuk kepada rujukan image_532b21.png) -->
            <div class="bg-white rounded-lg shadow-md mb-6 p-8 border border-gray-200 border-l-8 border-l-blue-500 relative">
                <div class="mb-6">
                    <h2 class="text-xl font-bold text-gray-900 mb-1">COURSE: <span class="text-red-500">*</span></h2>
                    <p class="text-gray-600 text-sm">Can choose more than one (1) course.</p>
                </div>

                <div class="space-y-4">
                    <!-- Pilihan 1 -->
                    <label class="flex items-center cursor-pointer group">
                        <input type="checkbox" name="course" value="Building First Systems" data-price="100" class="w-5 h-5 text-purple-600 border-gray-300 rounded focus:ring-purple-500 mr-4" onchange="calculateTotal()">
                        <span class="text-gray-800 group-hover:text-purple-700">BUILDING YOUR FIRST SYSTEMS USING AI (RM100)</span>
                    </label>
                    
                    <!-- Pilihan 2 -->
                    <label class="flex items-center cursor-pointer group">
                        <input type="checkbox" name="course" value="Mastering Gemini" data-price="50" class="w-5 h-5 text-purple-600 border-gray-300 rounded focus:ring-purple-500 mr-4" onchange="calculateTotal()">
                        <span class="text-gray-800 group-hover:text-purple-700">MASTERING GEMINI NOTEBOOK (NOTEBOOKLM) (RM50)</span>
                    </label>

                    <!-- Pilihan 3 -->
                    <label class="flex items-center cursor-pointer group">
                        <input type="checkbox" name="course" value="Zero to Pro Canva" data-price="50" class="w-5 h-5 text-purple-600 border-gray-300 rounded focus:ring-purple-500 mr-4" onchange="calculateTotal()">
                        <span class="text-gray-800 group-hover:text-purple-700">FROM ZERO TO PRO: CANVA POSTER (RM50)</span>
                    </label>

                    <!-- Pilihan 4 -->
                    <label class="flex items-center cursor-pointer group">
                        <input type="checkbox" name="course" value="Canva Education" data-price="100" class="w-5 h-5 text-purple-600 border-gray-300 rounded focus:ring-purple-500 mr-4" onchange="calculateTotal()">
                        <span class="text-gray-800 group-hover:text-purple-700">CANVA EDUCATION GAMES (RM100)</span>
                    </label>

                    <!-- Pilihan 5 -->
                    <label class="flex items-center cursor-pointer group">
                        <input type="checkbox" name="course" value="Canva Websites" data-price="50" class="w-5 h-5 text-purple-600 border-gray-300 rounded focus:ring-purple-500 mr-4" onchange="calculateTotal()">
                        <span class="text-gray-800 group-hover:text-purple-700">CANVA WEBSITES (RM50)</span>
                    </label>

                    <!-- Pilihan 6 -->
                    <label class="flex items-center cursor-pointer group">
                        <input type="checkbox" name="course" value="Get Certified Canva" data-price="50" class="w-5 h-5 text-purple-600 border-gray-300 rounded focus:ring-purple-500 mr-4" onchange="calculateTotal()">
                        <span class="text-gray-800 group-hover:text-purple-700">GET CERTIFIED WITH CANVA: FREE AI CERTIFICATION (RM50)</span>
                    </label>

                    <!-- Pilihan 7 -->
                    <label class="flex items-center cursor-pointer group">
                        <input type="checkbox" name="course" value="Websites Using Google" data-price="50" class="w-5 h-5 text-purple-600 border-gray-300 rounded focus:ring-purple-500 mr-4" onchange="calculateTotal()">
                        <span class="text-gray-800 group-hover:text-purple-700">WEBSITES USING GOOGLE (RM50)</span>
                    </label>

                    <!-- Pilihan 8 -->
                    <label class="flex items-center cursor-pointer group">
                        <input type="checkbox" name="course" value="TikTok Seller" data-price="50" class="w-5 h-5 text-purple-600 border-gray-300 rounded focus:ring-purple-500 mr-4" onchange="calculateTotal()">
                        <span class="text-gray-800 group-hover:text-purple-700">HOW TO BECOME TIKTOK SELLER (RM50)</span>
                    </label>

                    <!-- Pilihan 9 -->
                    <label class="flex items-center cursor-pointer group">
                        <input type="checkbox" name="course" value="Shopee Seller" data-price="50" class="w-5 h-5 text-purple-600 border-gray-300 rounded focus:ring-purple-500 mr-4" onchange="calculateTotal()">
                        <span class="text-gray-800 group-hover:text-purple-700">HOW TO BECOME SHOPEE SELLER (RM50)</span>
                    </label>

                    <!-- Pilihan 10 -->
                    <label class="flex items-center cursor-pointer group mb-4">
                        <input type="checkbox" name="course" value="Business Content AI" data-price="50" class="w-5 h-5 text-purple-600 border-gray-300 rounded focus:ring-purple-500 mr-4" onchange="calculateTotal()">
                        <span class="text-gray-800 group-hover:text-purple-700">CREATE BUSINESS CONTENT USING AI (RM50)</span>
                    </label>

                    <!-- Other Option -->
                    <label class="flex items-center">
                        <input type="checkbox" name="course" value="Other" class="w-5 h-5 text-purple-600 border-gray-300 rounded focus:ring-purple-500 mr-4">
                        <span class="text-gray-800 mr-2">Other:</span>
                        <input type="text" class="border-b-2 border-gray-300 focus:border-purple-600 focus:outline-none py-1 px-2 w-full md:w-1/2" placeholder="Sila nyatakan">
                    </label>
                </div>
            </div>

            <!-- Paparan Jumlah Bayaran & Butang Hantar -->
            <div class="bg-white rounded-lg shadow-md mb-8 p-6 flex flex-col md:flex-row justify-between items-center border border-gray-200">
                <div class="mb-4 md:mb-0">
                    <span class="text-gray-600 text-lg">Jumlah Yuran Pendaftaran:</span>
                    <div class="text-3xl font-bold text-purple-700 mt-1" id="totalDisplay">RM 0</div>
                </div>
                <button type="submit" class="w-full md:w-auto bg-purple-600 hover:bg-purple-700 text-white font-bold py-3 px-8 rounded-lg shadow transition">
                    Hantar Pendaftaran
                </button>
            </div>
            
            <div class="text-center pb-10 text-xs text-gray-500">
                Jangan hantar kata laluan atau maklumat sulit melalui borang ini.
            </div>

        </form>
    </div>

    <!-- Skrip Pengiraan Yuran -->
    <script>
        function calculateTotal() {
            let total = 0;
            // Dapatkan semua checkbox yang ditanda dan mempunyai atribut 'data-price'
            const checkboxes = document.querySelectorAll('input[name="course"]:checked');
            
            checkboxes.forEach(function(checkbox) {
                if(checkbox.getAttribute('data-price')) {
                    total += parseInt(checkbox.getAttribute('data-price'));
                }
            });
            
            // Kemas kini paparan jumlah di skrin
            document.getElementById('totalDisplay').innerText = 'RM ' + total;
        }
    </script>
</body>
</html>
