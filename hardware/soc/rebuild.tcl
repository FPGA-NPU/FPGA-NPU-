# Recreate the minimal Zybo Z7-20 SoC project from repository sources.
# Vivado 2024.2

set script_dir   [file normalize [file dirname [info script]]]
set hardware_dir [file normalize [file join $script_dir ..]]
set repo_root    [file normalize [file join $hardware_dir ..]]
set project_name fpga_npu_v6
set build_dir    [file join $repo_root build vivado]
set ip_repo_dir  [file join $hardware_dir npu]
set bd_file      [file join $script_dir design_SoC.bd]
set wrapper_file [file join $script_dir design_SoC_wrapper.v]
set xdc_file     [file join $script_dir constraints audio_io.xdc]

foreach f [list $bd_file $wrapper_file $xdc_file [file join $ip_repo_dir component.xml]] {
    if {![file exists $f]} { error "Missing required source: $f" }
}

create_project $project_name $build_dir -part xc7z020clg400-1 -force
set_property ip_repo_paths [list $ip_repo_dir] [current_project]
update_ip_catalog

add_files -norecurse $bd_file
add_files -norecurse $wrapper_file
add_files -fileset constrs_1 -norecurse $xdc_file

open_bd_design $bd_file
validate_bd_design
generate_target all [get_files design_SoC.bd]
update_compile_order -fileset sources_1
set_property top design_SoC_wrapper [current_fileset]

puts "PROJECT_CREATED=[get_property DIRECTORY [current_project]]"
puts "Next: launch_runs synth_1 / impl_1 as needed."
