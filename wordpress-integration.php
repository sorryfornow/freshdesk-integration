<?php
/**
 * Theme functions and definitions
 *
 * @package HelloBiz
 */

use HelloBiz\Theme;

if ( ! defined( 'ABSPATH' ) ) {
	exit; // Exit if accessed directly.
}

define( 'HELLO_BIZ_ELEMENTOR_VERSION', '1.1.0' );
define( 'EHP_THEME_SLUG', 'hello-biz' );

define( 'HELLO_BIZ_PATH', get_template_directory() );
define( 'HELLO_BIZ_URL', get_template_directory_uri() );
define( 'HELLO_BIZ_ASSETS_PATH', HELLO_BIZ_PATH . '/build/' );
define( 'HELLO_BIZ_ASSETS_URL', HELLO_BIZ_URL . '/build/' );
define( 'HELLO_BIZ_SCRIPTS_PATH', HELLO_BIZ_ASSETS_PATH . 'js/' );
define( 'HELLO_BIZ_SCRIPTS_URL', HELLO_BIZ_ASSETS_URL . 'js/' );
define( 'HELLO_BIZ_STYLE_PATH', HELLO_BIZ_ASSETS_PATH . 'css/' );
define( 'HELLO_BIZ_STYLE_URL', HELLO_BIZ_ASSETS_URL . 'css/' );
define( 'HELLO_BIZ_IMAGES_PATH', HELLO_BIZ_ASSETS_PATH . 'images/' );
define( 'HELLO_BIZ_IMAGES_URL', HELLO_BIZ_ASSETS_URL . 'images/' );
define( 'HELLO_BIZ_STARTER_IMAGES_PATH', HELLO_BIZ_IMAGES_PATH . 'starter-content/' );
define( 'HELLO_BIZ_STARTER_IMAGES_URL', HELLO_BIZ_IMAGES_URL . 'starter-content/' );

if ( ! isset( $content_width ) ) {
	$content_width = 800; // Pixels.
}

// Init the Theme class
require HELLO_BIZ_PATH . '/theme.php';

Theme::instance();

// hide bar
add_filter('show_admin_bar', '__return_false');

// NEW ADDED FUNC

// Equipment Repair Form - Simplified Version
// =========================================

// Add JavaScript for reference number
add_action('wp_head', function() {
    if (is_page('repairs')) {
        ?>
        <script>
        // Generate reference number
        function generateReferenceNumber() {
            const prefix = "1CYBRPR";
            const timestamp = Date.now().toString().slice(-6);
            const random = Math.floor(Math.random() * 9999).toString().padStart(4, '0');
            return prefix + timestamp + random;
        }

        // Store reference number globally
        var repairReferenceNumber = generateReferenceNumber();
        </script>
        <?php
    }
});

// Custom confirmation message
add_filter('wpforms_frontend_confirmation_message', function($message, $form_data) {
    if ($form_data['id'] == 107) {
        $reference = isset($_POST['wpforms']['fields']['39']) ? $_POST['wpforms']['fields']['39'] : 'N/A';

        $message = '<div style="text-align: center; padding: 40px; max-width: 600px; margin: 0 auto;">
            <h2>Request Submitted Successfully!</h2>
            <p>Your repair request has been received.</p>
            <p style="font-size: 24px; color: #007cba;">Reference: ' . esc_html($reference) . '</p>
            <p>A confirmation email has been sent.</p>
        </div>';
    }
    return $message;
}, 10, 2);




// Freshdesk
/**
 * 1CYBER Repair Form - Freshdesk Integration
 *
 * This code integrates WPForms ID #107 with Freshdesk API
 * Add this code to the end of your functions.php file
 */

// ===========================================
// CONFIGURATION - UPDATE FOR PRODUCTION
// ===========================================
// Development API URL - UPDATE WITH NGROK URL

// API URLs - ngrok
define('FRESHDESK_API_DEV_URL', 'https://ad9f-144-6-49-146.ngrok-free.app/webhook/wordpress');
define('FRESHDESK_API_PROD_URL', 'https://api.1cyber.com.au/webhook/wordpress');

// Environment setting - Change to 'production' when deploying
define('REPAIR_FORM_ENV', 'development');

// Target form ID
define('REPAIR_FORM_ID', 107);

// ===========================================
// MAIN INTEGRATION FUNCTION
// ===========================================

/**
 * Get API URL based on environment
 */
function get_repair_api_url() {
    return (REPAIR_FORM_ENV === 'production') ? FRESHDESK_API_PROD_URL : FRESHDESK_API_DEV_URL;
}

/**
 * WPForms Integration for Repair Form
 */
add_action('wpforms_process_complete', function($fields, $entry, $form_data) {

    // Only process our repair form (ID #107)
    if ($form_data['id'] != REPAIR_FORM_ID) {
        return;
    }

    // Log form submission
    error_log('1CYBER Repair Form: Processing submission for form ID: ' . $form_data['id']);

    // Extract form data using field IDs
    $form_fields = array();

    foreach ($fields as $field_id => $field_data) {
        $value = $field_data['value'];

        // Map based on your specific field IDs
        switch ($field_id) {
            case '10': // Contact Full Name
                $form_fields['contact_name'] = $value;
                break;
            case '11': // Business Name
                $form_fields['business_name'] = $value;
                break;
            case '12': // Contact Number
                $form_fields['contact_phone'] = $value;
                break;
            case '38': // Contact Email
                $form_fields['contact_email'] = $value;
                break;
            case '14': // User Profile Name
                $form_fields['user_profile_name'] = $value;
                break;
            case '15': // User Profile Password
                $form_fields['user_profile_password'] = $value;
                break;
            case '18': // Equipment
                $form_fields['equipment_type'] = $value;
                break;
            case '19': // Store
                $form_fields['store_location'] = $value;
                break;
            case '20': // Brand
                $form_fields['equipment_brand'] = $value;
                break;
            case '21': // Model
                $form_fields['equipment_model'] = $value;
                break;
            case '22': // Serial Number
                $form_fields['serial_number'] = $value;
                break;
            case '23': // Fault Description
                $form_fields['fault_description'] = $value;
                break;
            case '35': // Accessories Included
                $form_fields['accessories'] = $value;
                break;
            case '36': // Others - Please comment
                $form_fields['additional_comments'] = $value;
                break;
            case '37': // File Upload
                $form_fields['uploaded_files'] = $value;
                break;
            case '39': // Hidden Field (Ticket ID)
                $form_fields['internal_ticket_id'] = $value;
                break;
            case '43': // Date
                $form_fields['repair_date'] = $value;
                break;
            case '44': // Time
                $form_fields['repair_time'] = $value;
                break;
        }
    }

    // Create comprehensive ticket data
    $ticket_data = array(
        'name' => $form_fields['contact_name'] ?? 'Unknown Customer',
        'email' => $form_fields['contact_email'] ?? '',
        'phone' => $form_fields['contact_phone'] ?? '',
        'company' => $form_fields['business_name'] ?? '',
        'subject' => 'Equipment Repair Request - ' . ($form_fields['equipment_type'] ?? 'Unknown Equipment'),
        'message' => create_repair_ticket_description($form_fields),
        'priority' => 'medium',
        'ticket_type' => 'Problem',
        'tags' => array('repair', 'equipment', $form_fields['equipment_type'] ?? 'unknown'),
        'custom_fields' => array(
            'equipment_brand' => $form_fields['equipment_brand'] ?? '',
            'equipment_model' => $form_fields['equipment_model'] ?? '',
            'serial_number' => $form_fields['serial_number'] ?? '',
            'store_location' => $form_fields['store_location'] ?? '',
            'repair_date' => $form_fields['repair_date'] ?? '',
            'repair_time' => $form_fields['repair_time'] ?? '',
            'internal_ticket_id' => $form_fields['internal_ticket_id'] ?? ''
        ),
        'source_url' => 'https://repairs.1cyber.com.au/',
        'form_id' => REPAIR_FORM_ID,
        'submission_time' => current_time('mysql'),
        'form_type' => 'repair_request'
    );

    // Send to Freshdesk API
    $response = send_repair_data_to_api($ticket_data);

    if ($response['success']) {
        error_log('1CYBER Repair: Freshdesk ticket created successfully - ID: ' . $response['ticket_id']);

        // Store ticket ID for reference
        update_option('last_repair_ticket_id', $response['ticket_id']);
        update_option('last_repair_submission', json_encode($form_fields));

    } else {
        error_log('1CYBER Repair: Failed to create Freshdesk ticket - ' . $response['error']);

        // Send email notification as fallback
        send_repair_fallback_email($form_fields, $response['error']);
    }

}, 10, 3);

/**
 * Create detailed ticket description for repair request
 */
function create_repair_ticket_description($fields) {

    $description = "=== EQUIPMENT REPAIR REQUEST ===\n\n";

    // Customer Information
    $description .= "CUSTOMER DETAILS:\n";
    $description .= "Contact Name: " . ($fields['contact_name'] ?? 'Not provided') . "\n";
    $description .= "Business Name: " . ($fields['business_name'] ?? 'Not provided') . "\n";
    $description .= "Phone: " . ($fields['contact_phone'] ?? 'Not provided') . "\n";
    $description .= "Email: " . ($fields['contact_email'] ?? 'Not provided') . "\n\n";

    // Equipment Details
    $description .= "EQUIPMENT INFORMATION:\n";
    $description .= "Equipment Type: " . ($fields['equipment_type'] ?? 'Not specified') . "\n";
    $description .= "Brand: " . ($fields['equipment_brand'] ?? 'Not specified') . "\n";
    $description .= "Model: " . ($fields['equipment_model'] ?? 'Not specified') . "\n";
    $description .= "Serial Number: " . ($fields['serial_number'] ?? 'Not provided') . "\n\n";

    // Service Details
    $description .= "SERVICE DETAILS:\n";
    $description .= "Store Location: " . ($fields['store_location'] ?? 'Not specified') . "\n";
    $description .= "Preferred Date: " . ($fields['repair_date'] ?? 'Not specified') . "\n";
    $description .= "Preferred Time: " . ($fields['repair_time'] ?? 'Not specified') . "\n\n";

    // Problem Description
    $description .= "FAULT DESCRIPTION:\n";
    $description .= ($fields['fault_description'] ?? 'No description provided') . "\n\n";

    // Accessories
    if (!empty($fields['accessories'])) {
        $description .= "ACCESSORIES INCLUDED:\n";
        $description .= $fields['accessories'] . "\n\n";
    }

    // Additional Comments
    if (!empty($fields['additional_comments'])) {
        $description .= "ADDITIONAL COMMENTS:\n";
        $description .= $fields['additional_comments'] . "\n\n";
    }

    // User Profile Information
    if (!empty($fields['user_profile_name'])) {
        $description .= "USER ACCOUNT:\n";
        $description .= "Profile Name: " . $fields['user_profile_name'] . "\n";
        if (!empty($fields['user_profile_password'])) {
            $description .= "Password Provided: Yes\n";
        }
        $description .= "\n";
    }

    // Internal Reference
    if (!empty($fields['internal_ticket_id'])) {
        $description .= "INTERNAL REFERENCE:\n";
        $description .= "Internal Ticket ID: " . $fields['internal_ticket_id'] . "\n\n";
    }

    // File Uploads
    if (!empty($fields['uploaded_files'])) {
        $description .= "UPLOADED FILES:\n";
        $description .= "Customer has uploaded photos/documents (see attachments)\n\n";
    }

    $description .= "=== END OF REPAIR REQUEST ===";

    return $description;
}

/**
 * Send data to Flask API
 */
function send_repair_data_to_api($ticket_data) {

    $api_url = get_repair_api_url();

    $args = array(
        'method' => 'POST',
        'timeout' => 45,
        'headers' => array(
            'Content-Type' => 'application/json',
            'User-Agent' => '1CYBER-Repair-Form/1.0'
        ),
        'body' => json_encode($ticket_data)
    );

    $response = wp_remote_post($api_url, $args);

    if (is_wp_error($response)) {
        return array(
            'success' => false,
            'error' => $response->get_error_message()
        );
    }

    $response_code = wp_remote_retrieve_response_code($response);
    $response_body = wp_remote_retrieve_body($response);

    if ($response_code === 200) {
        $decoded_response = json_decode($response_body, true);

        if ($decoded_response && $decoded_response['status'] === 'success') {
            return array(
                'success' => true,
                'ticket_id' => $decoded_response['ticket_created']['id'] ?? 'unknown',
                'response' => $decoded_response
            );
        }
    }

    return array(
        'success' => false,
        'error' => 'API Error: ' . $response_body,
        'response_code' => $response_code
    );
}

/**
 * Fallback email notification if API fails
 */
function send_repair_fallback_email($fields, $api_error) {

    $admin_email = 'siqing.zhang@1cyber.com.au';
    $subject = 'URGENT: Repair Form Submission - API Failed';

    $message = "A repair form was submitted but the Freshdesk API failed.\n\n";
    $message .= "API Error: " . $api_error . "\n\n";
    $message .= "Form Data:\n";
    $message .= print_r($fields, true);
    $message .= "\n\nPlease manually create a Freshdesk ticket for this customer.";

    wp_mail($admin_email, $subject, $message);
}

// ===========================================
// ADMIN FUNCTIONS
// ===========================================

/**
 * Add admin menu for testing
 */
add_action('admin_menu', function() {
    add_options_page(
        '1CYBER Repair Integration',
        'Repair Integration',
        'manage_options',
        '1cyber-repair-integration',
        'repair_integration_admin_page'
    );
});

/**
 * Admin page for testing and monitoring
 */
function repair_integration_admin_page() {

    // Handle test submission
    if (isset($_POST['test_repair_api']) && wp_verify_nonce($_POST['_wpnonce'], 'test_repair_api')) {

        $test_data = array(
            'name' => 'Test Customer',
            'email' => 'siqing.zhang@1cyber.com.au',
            'phone' => '0400000000',
            'company' => 'Test Business',
            'subject' => 'Test Equipment Repair - API Test',
            'message' => create_repair_ticket_description(array(
                'contact_name' => 'Test Customer',
                'business_name' => 'Test Business',
                'contact_phone' => '0400000000',
                'contact_email' => 'siqing.zhang@1cyber.com.au',
                'equipment_type' => 'Laptop',
                'equipment_brand' => 'Dell',
                'equipment_model' => 'Inspiron 15',
                'serial_number' => 'TEST123456',
                'fault_description' => 'Screen not working - test submission',
                'store_location' => 'Sydney',
                'repair_date' => date('Y-m-d'),
                'repair_time' => '10:00 AM'
            )),
            'priority' => 'low',
            'ticket_type' => 'Problem',
            'form_type' => 'repair_request_test'
        );

        $result = send_repair_data_to_api($test_data);

        if ($result['success']) {
            echo '<div class="notice notice-success"><p>✅ Test successful! Ticket ID: ' . $result['ticket_id'] . '</p></div>';
        } else {
            echo '<div class="notice notice-error"><p>❌ Test failed: ' . $result['error'] . '</p></div>';
        }
    }

    ?>
    <div class="wrap">
        <h1>1CYBER Repair Form Integration</h1>

        <h2>Current Configuration</h2>
        <table class="form-table">
            <tr>
                <th>Environment:</th>
                <td><?php echo REPAIR_FORM_ENV; ?></td>
            </tr>
            <tr>
                <th>API URL:</th>
                <td><?php echo get_repair_api_url(); ?></td>
            </tr>
            <tr>
                <th>Form ID:</th>
                <td><?php echo REPAIR_FORM_ID; ?></td>
            </tr>
            <tr>
                <th>Last Ticket ID:</th>
                <td><?php echo get_option('last_repair_ticket_id', 'None'); ?></td>
            </tr>
        </table>

        <h2>Test API Connection</h2>
        <form method="post">
            <?php wp_nonce_field('test_repair_api'); ?>
            <input type="submit" name="test_repair_api" class="button-primary" value="Send Test Repair Request" />
        </form>

        <h2>Recent Submission Data</h2>
        <?php
        $last_submission = get_option('last_repair_submission', '{}');
        $submission_data = json_decode($last_submission, true);

        if (!empty($submission_data)) {
            echo '<pre>' . print_r($submission_data, true) . '</pre>';
        } else {
            echo '<p>No recent submissions found.</p>';
        }
        ?>

        <h2>Production Deployment</h2>
        <p><strong>When ready for production:</strong></p>
        <ol>
            <li>Change <code>REPAIR_FORM_ENV</code> to <code>'production'</code></li>
            <li>Update your Flask app environment to production</li>
            <li>Test the integration thoroughly</li>
        </ol>
    </div>
    <?php
}

// ===========================================
// DEBUGGING AND LOGGING
// ===========================================

/**
 * Enhanced logging for repair form
 */
function log_repair_integration($message, $data = null) {
    $log_message = '[1CYBER Repair Integration] ' . $message;

    if ($data) {
        $log_message .= ' | Data: ' . json_encode($data);
    }

    error_log($log_message);
}

/**
 * Debug form fields (for admin users only)
 */
add_action('wp_footer', function() {
    if (current_user_can('administrator') && isset($_GET['debug_repair_form'])) {
        ?>
        <script>
            console.log('1CYBER Repair Form Debug Mode Active');

            document.addEventListener('submit', function(e) {
                if (e.target.querySelector('[name*="wpforms"]')) {
                    console.log('Repair form submitted with data:');
                    const formData = new FormData(e.target);
                    for (let [key, value] of formData.entries()) {
                        console.log(key + ': ' + value);
                    }
                }
            });
        </script>
        <?php
    }
});

// Add notification for successful integration
add_action('init', function() {
    if (current_user_can('administrator')) {
        error_log('1CYBER Repair Form Integration loaded successfully');
    }
});

// 1Cyber Equipment Repair - Direct Freshdesk Integration
add_action('wpforms_process_complete_107', 'send_repair_to_freshdesk', 10, 4);

function send_repair_to_freshdesk($fields, $entry, $form_data, $entry_id) {

    $webhook_url = 'https://ad9f-144-6-49-146.ngrok-free.app/webhook/wordpress';

    $data = array(
        'wpforms' => array(
            'id' => '107',
            'fields' => array(
                '10' => isset($fields[10]) ? $fields[10]['value'] : '',
                '11' => isset($fields[11]) ? $fields[11]['value'] : '',
                '12' => isset($fields[12]) ? $fields[12]['value'] : '',
                '38' => isset($fields[38]) ? $fields[38]['value'] : '',
                '14' => isset($fields[14]) ? $fields[14]['value'] : '',
                '15' => isset($fields[15]) ? $fields[15]['value'] : '',
                '18' => isset($fields[18]) ? $fields[18]['value'] : '',
                '19' => isset($fields[19]) ? $fields[19]['value'] : '',
                '20' => isset($fields[20]) ? $fields[20]['value'] : '',
                '21' => isset($fields[21]) ? $fields[21]['value'] : '',
                '22' => isset($fields[22]) ? $fields[22]['value'] : '',
                '23' => isset($fields[23]) ? $fields[23]['value'] : '',
                '35' => isset($fields[35]) ? $fields[35]['value'] : '',
                '36' => isset($fields[36]) ? $fields[36]['value'] : '',
                '37' => isset($fields[37]) ? $fields[37]['value'] : '',
                '39' => isset($fields[39]) ? $fields[39]['value'] : '',
                '43' => isset($fields[43]) ? $fields[43]['value'] : '',
                '44' => isset($fields[44]) ? $fields[44]['value'] : ''
            )
        )
    );

    wp_remote_post($webhook_url, array(
        'method' => 'POST',
        'headers' => array('Content-Type' => 'application/json'),
        'body' => json_encode($data),
        'timeout' => 30
    ));
}
