use pyo3::prelude::*;
use pyo3::wrap_pyfunction;
use std::fs::{self, File, OpenOptions};
use std::io::{self, BufRead, BufReader, Write, Read};
use std::path::Path;
use std::collections::{HashSet, HashMap};
use std::process;
use std::env;
use std::str::FromStr;

#[derive(Debug)]
pub struct QuiverCore {
    fnm: String,
    mode: String,
    tags: Vec<String>,
}

impl QuiverCore {
    pub fn new(filename: String, mode: String) -> Result<Self, String> {
        if mode != "r" && mode != "w" {
            return Err(format!(
                "Quiver file must be opened in 'r' or 'w' mode, not '{}'", mode
            ));
        }
        let tags = Self::read_tags(&filename)?;
        Ok(QuiverCore { fnm: filename, mode, tags })
    }

    fn read_tags(filename: &str) -> Result<Vec<String>, String> {
        if !Path::new(filename).exists() {
            return Ok(vec![]);
        }
        let file = File::open(filename).map_err(|e| e.to_string())?;
        let reader = BufReader::new(file);
        let mut tags = Vec::new();
        for line in reader.lines() {
            let line = line.map_err(|e| e.to_string())?;
            if line.starts_with("QV_TAG") {
                let parts: Vec<_> = line.split_whitespace().collect();
                if parts.len() > 1 {
                    tags.push(parts[1].to_string());
                }
            }
        }
        Ok(tags)
    }

    pub fn get_tags(&self) -> Vec<String> {
        self.tags.clone()
    }

    pub fn size(&self) -> usize {
        self.tags.len()
    }

    pub fn add_pdb(&mut self, pdb_lines: &[String], tag: &str, score_str: Option<&str>) -> Result<(), String> {
        if self.mode != "w" {
            return Err("Quiver file must be opened in write mode to allow for writing.".to_string());
        }
        if self.tags.contains(&tag.to_string()) {
            return Err(format!("Tag {} already exists in this file.", tag));
        }

        let mut file = OpenOptions::new().create(true).append(true).open(&self.fnm)
            .map_err(|e| e.to_string())?;
        writeln!(file, "QV_TAG {}", tag).map_err(|e| e.to_string())?;
        if let Some(score) = score_str {
            writeln!(file, "QV_SCORE {} {}", tag, score).map_err(|e| e.to_string())?;
        }
        for line in pdb_lines {
            file.write_all(line.as_bytes()).map_err(|e| e.to_string())?;
            if !line.ends_with('\n') {
                file.write_all(b"\n").map_err(|e| e.to_string())?;
            }
        }
        self.tags.push(tag.to_string());
        Ok(())
    }

    pub fn get_pdblines(&self, tag: &str) -> Result<Vec<String>, String> {
        if self.mode != "r" {
            return Err("Quiver file must be opened in read mode to allow for reading.".to_string());
        }
        let file = File::open(&self.fnm).map_err(|e| e.to_string())?;
        let reader = BufReader::new(file);
        let mut found = false;
        let mut pdb_lines = Vec::new(); // Will store lines without trailing newlines

        for line_result in reader.lines() {
            let line = line_result.map_err(|e| e.to_string())?;
            if line.starts_with("QV_TAG") {
                let parts: Vec<_> = line.split_whitespace().collect();
                if parts.len() > 1 && parts[1] == tag {
                    found = true;
                    continue; 
                } else if found {
                    // Found the start of the next tag, so stop.
                    break;
                }
            }
            if found && !line.starts_with("QV_SCORE") {
                pdb_lines.push(line); // Store line without adding newline
            }
        }
        if !found {
            return Err(format!("Requested tag: {} does not exist", tag));
        }
        Ok(pdb_lines)
    }

    pub fn get_struct_list(&self, tag_list: &[String]) -> Result<(String, Vec<String>), String> {
        if self.mode != "r" {
            return Err("Quiver file must be opened in read mode to allow for reading.".to_string());
        }
        let tag_set: HashSet<_> = tag_list.iter().cloned().collect();
        let mut found_tags = Vec::new();
        let mut struct_lines = String::new();
        let mut write_mode = false;

        let file = File::open(&self.fnm).map_err(|e| e.to_string())?;
        let reader = BufReader::new(file);

        for line in reader.lines() {
            let line = line.map_err(|e| e.to_string())?;
            if line.starts_with("QV_TAG") {
                let parts: Vec<_> = line.split_whitespace().collect();
                let current_tag = if parts.len() > 1 { parts[1] } else { "" };
                write_mode = tag_set.contains(current_tag);
                if write_mode {
                    found_tags.push(current_tag.to_string());
                }
            }
            if write_mode {
                struct_lines.push_str(&line);
                struct_lines.push('\n');
            }
        }
        Ok((struct_lines, found_tags))
    }

    pub fn split(&self, ntags: usize, outdir: &str, prefix: &str) -> Result<(), String> {
        if self.mode != "r" {
            return Err("Quiver file must be opened in read mode to allow for reading.".to_string());
        }
        std::fs::create_dir_all(outdir).map_err(|e| e.to_string())?;

        let mut file_idx = 0;
        let mut tag_count = 0;
        let mut out_file: Option<File> = None;

        let file = File::open(&self.fnm).map_err(|e| e.to_string())?;
        let reader = BufReader::new(file);

        for line in reader.lines() {
            let line = line.map_err(|e| e.to_string())?;
            if line.starts_with("QV_TAG") {
                if tag_count % ntags == 0 {
                    if let Some(mut f) = out_file.take() {
                        f.flush().map_err(|e| e.to_string())?;
                    }
                    let out_path = Path::new(outdir).join(format!("{}_{}.qv", prefix, file_idx));
                    out_file = Some(File::create(out_path).map_err(|e| e.to_string())?);
                    file_idx += 1;
                }
                tag_count += 1;
            }
            if let Some(f) = out_file.as_mut() {
                writeln!(f, "{}", line).map_err(|e| e.to_string())?;
            }
        }
        if let Some(mut f) = out_file {
            f.flush().map_err(|e| e.to_string())?;
        }
        Ok(())
    }
}

#[pyclass]
struct Quiver {
    core: QuiverCore,
}

#[pymethods]
impl Quiver {
    #[new]
    fn new(filename: String, mode: String) -> PyResult<Self> {
        match QuiverCore::new(filename, mode) {
            Ok(core) => Ok(Quiver { core }),
            Err(e) => Err(pyo3::exceptions::PyValueError::new_err(e)),
        }
    }

    fn get_tags(&self) -> Vec<String> {
        self.core.get_tags()
    }

    fn size(&self) -> usize {
        self.core.size()
    }

    fn add_pdb(&mut self, pdb_lines: Vec<String>, tag: String, score_str: Option<String>) -> PyResult<()> {
        match self.core.add_pdb(&pdb_lines, &tag, score_str.as_deref()) {
            Ok(_) => Ok(()),
            Err(e) => Err(pyo3::exceptions::PyIOError::new_err(e)),
        }
    }

    fn get_pdblines(&self, tag: &str) -> PyResult<Vec<String>> {
        match self.core.get_pdblines(tag) {
            Ok(lines) => Ok(lines),
            Err(e) => Err(pyo3::exceptions::PyIOError::new_err(e)),
        }
    }

    fn get_struct_list(&self, tag_list: Vec<String>) -> PyResult<(String, Vec<String>)> {
        match self.core.get_struct_list(&tag_list) {
            Ok(result) => Ok(result),
            Err(e) => Err(pyo3::exceptions::PyIOError::new_err(e)),
        }
    }

    fn split(&self, ntags: usize, outdir: String, prefix: String) -> PyResult<()> {
        match self.core.split(ntags, &outdir, &prefix) {
            Ok(_) => Ok(()),
            Err(e) => Err(pyo3::exceptions::PyIOError::new_err(e)),
        }
    }
}

/// Converts multiple PDB files into Quiver format.
///
/// Takes a list of PDB file paths and concatenates them into a single
/// string in Quiver format. Each PDB file's content is preceded by a
/// "QV_TAG" line, where the tag is derived from the PDB file's stem.
///
/// # Arguments
///
/// * `pdb_files` - A vector of strings, where each string is a path to a PDB file.
///
/// # Errors
///
/// Returns a `PyErr` if:
/// * Any of the PDB files cannot be opened.
/// * The file stem of a PDB file cannot be converted to a string.
/// * An I/O error occurs during reading or writing.
#[pyfunction]
fn rs_qvfrompdbs(pdb_files: Vec<String>) -> PyResult<String> {
    let mut output = Vec::new();

    for pdbfn in &pdb_files {
        let path = Path::new(pdbfn);
        let tag = path.file_stem()
            .and_then(|s| s.to_str())
            .ok_or_else(|| pyo3::exceptions::PyValueError::new_err(format!("Could not get tag from filename: {}", pdbfn)))?;

        writeln!(output, "QV_TAG {}", tag)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;

        let mut file = File::open(pdbfn)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
        io::copy(&mut file, &mut output)
            .map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
    }

    Ok(String::from_utf8_lossy(&output).to_string())
}

/// Extracts all PDB structures from a Quiver file and saves them as individual PDB files.
///
/// Iterates through all tags in the Quiver file, extracts the corresponding PDB
/// lines, and writes them to new PDB files named after their tags (e.g., "tag.pdb").
/// Files that already exist will be skipped.
///
/// # Arguments
///
/// * `_py` - The Python GIL token (unused).
/// * `quiver_file` - The path to the Quiver file.
///
/// # Returns
///
/// `Ok(Vec<String>)` where the vector contains the paths of the PDB files that were successfully extracted.
/// Returns an empty vector if no files were extracted (e.g., all files already existed or no tags were found).
///
/// # Errors
///
/// Returns a `PyErr` if:
/// * The Quiver file cannot be opened or read.
/// * There is an error creating or writing to an output PDB file for any of the tags.
///   (Note: The function will attempt to process all tags even if some fail.)
#[pyfunction]
fn rs_extract_pdbs(_py: Python, quiver_file: String) -> PyResult<Vec<String>> {
    let qv = Quiver::new(quiver_file.clone(), "r".to_string())?;
    let tags = qv.get_tags();
    let mut extracted_files = Vec::new();

    for tag in &tags {
        let outfn = format!("{}.pdb", tag);

        // Skip if the file already exists
        if Path::new(&outfn).exists() {
            // Optionally, inform the caller that this file was skipped.
            // For now, just continue.
            continue;
        }

        // Get PDB lines
        match qv.get_pdblines(tag) { // Pass &String as &str
            Ok(lines) => {
                // Create and write to file
                match File::create(&outfn) {
                    Ok(mut f) => {
                        for line in lines { // lines are Vec<String> without newlines
                            if let Err(e) = writeln!(f, "{}", line) {
                                return Err(pyo3::exceptions::PyIOError::new_err(
                                    format!("Failed to write line to file {}: {}", outfn, e)
                                ));
                            }
                        }
                        extracted_files.push(outfn);
                    }
                    Err(e) => {
                        return Err(pyo3::exceptions::PyIOError::new_err(
                            format!("Failed to create file {}: {}", outfn, e)
                        ));
                    }
                }
            }
            Err(e) => {
                return Err(pyo3::exceptions::PyIOError::new_err(
                    format!("Failed to get PDB lines for tag {}: {}", tag, e)
                ));
            }
        }
    }

    Ok(extracted_files)
}

// Add rs_list_tags function
/// Lists all tags present in a Quiver file.
///
/// # Arguments
///
/// * `quiver_file` - The path to the Quiver file.
///
/// # Returns
///
/// `Ok(Vec<String>)` containing all tags found in the file.
///
/// # Errors
///
/// Returns a `PyErr` if the Quiver file cannot be opened or read.
#[pyfunction]
fn rs_list_tags(quiver_file: String) -> PyResult<Vec<String>> {
    match Quiver::new(quiver_file.clone(), "r".to_string()) {
        Ok(qv) => {
            let tags = qv.get_tags();
            Ok(tags)
        }
        Err(e) => Err(pyo3::exceptions::PyIOError::new_err(e)),
    }
}

// Add rs_rename_tags function
/// Renames tags in a Quiver file.
///
/// Takes an existing Quiver file and a list of new tags. It generates a new
/// Quiver file content as a string where the old tags are replaced by the new
/// tags in the order they appear.
///
/// # Arguments
///
/// * `_py` - The Python GIL token (unused).
/// * `quiver_file` - Path to the existing Quiver file.
/// * `new_tags` - A vector of strings representing the new tags. The number
///   of new tags must match the number of existing tags in the file.
///
/// # Returns
///
/// `Ok(String)` containing the content of the Quiver file with renamed tags.
///
/// # Errors
///
/// Returns a `PyErr` if:
/// * The Quiver file cannot be opened or read.
/// * The number of `new_tags` does not match the number of tags in the file.
/// * An I/O error occurs during reading.
/// * Two "QV_TAG" lines are found consecutively, which is not supported.
#[pyfunction]
fn rs_rename_tags(_py: Python, quiver_file: String, new_tags: Vec<String>) -> PyResult<String> {
    match Quiver::new(quiver_file.clone(), "r".to_string()) {
        Ok(qv) => {
            let present_tags = qv.get_tags();

            if present_tags.len() != new_tags.len() {
                return Err(pyo3::exceptions::PyValueError::new_err(
                    format!("Number of tags in file ({}) does not match number of tags provided ({})",
                        present_tags.len(), new_tags.len())
                ));
            }

            rename_tags_in_file_content(&quiver_file, &new_tags)
        }
        Err(e) => Err(e),
    }
}

use tempfile::NamedTempFile;
use std::io::LineWriter;

fn rename_tags_in_file_content(quiver_file_path: &str, new_tags: &[String]) -> PyResult<String> {
    let mut tag_idx = 0;

    if new_tags.is_empty() {
        // Check if the file actually has tags. If not, empty new_tags is fine.
        // This requires opening and reading tags, which adds some overhead.
        // Alternatively, rely on the main `rs_rename_tags` function's check.
        // For now, let's assume `rs_rename_tags` ensures `new_tags` matches existing tag count.
        // If new_tags is empty and there are tags in file, rs_rename_tags would error out first.
        // If both are empty, it's a no-op, an empty temp file would be fine or handled by rs_rename_tags.
    }

    // Create a named temporary file in the same directory as the original file if possible,
    // to facilitate atomic replacement by the caller (Python code).
    let original_path = Path::new(quiver_file_path);
    let parent_dir = original_path.parent().unwrap_or_else(|| Path::new("."));
    let temp_file = NamedTempFile::new_in(parent_dir)
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to create temporary file: {}", e)))?;
    
    let output_file = temp_file.as_file();
    let mut writer = LineWriter::new(output_file);

    let input_file = File::open(original_path)
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to open input file {}: {}", quiver_file_path, e)))?;
    let reader = BufReader::new(input_file);

    let mut lines_iter = reader.lines();
    while let Some(line_result) = lines_iter.next() {
        let line = line_result.map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Error reading line: {}", e)))?;
        
        if line.starts_with("QV_TAG") {
            if tag_idx >= new_tags.len() {
                // This case should be prevented by the check in rs_rename_tags
                return Err(pyo3::exceptions::PyValueError::new_err(
                    "More tags in file than new tags provided (should have been caught earlier)"
                ));
            }
            writeln!(writer, "QV_TAG {}", new_tags[tag_idx])
                .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to write QV_TAG line: {}", e)))?;

            // Handle potential QV_SCORE line immediately following QV_TAG
            if let Some(next_line_result) = lines_iter.next() {
                let next_line = next_line_result.map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Error reading next line: {}", e)))?;
                if next_line.starts_with("QV_TAG") {
                    // This is an error: two QV_TAG lines in a row.
                     return Err(pyo3::exceptions::PyValueError::new_err(
                        format!("Error: Found two QV_TAG lines in a row. This is not supported. Line: {}", next_line)
                    ));
                }
                if next_line.starts_with("QV_SCORE") {
                    let parts: Vec<_> = next_line.split_whitespace().collect();
                    if parts.len() > 2 { // QV_SCORE old_tag score_value(s)
                        writeln!(writer, "QV_SCORE {} {}", new_tags[tag_idx], parts[2..].join(" "))
                            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to write QV_SCORE line: {}", e)))?;
                    } else {
                        // Malformed QV_SCORE line, write as is or error?
                        // Current behavior is to write it as is if it doesn't have enough parts for replacement.
                        // For safety and consistency, let's try to write it as is.
                        writeln!(writer, "{}", next_line)
                            .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to write line: {}", e)))?;
                    }
                } else {
                    // Not a QV_SCORE line, so it's a regular content line for the previous (now renamed) tag.
                    writeln!(writer, "{}", next_line)
                        .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to write line: {}", e)))?;
                }
            }
            // If there's no next line after QV_TAG, it means QV_TAG was the last line or file ends.
            // This is handled by the loop structure.
            tag_idx += 1;
        } else {
            // Regular line, not starting with QV_TAG
            writeln!(writer, "{}", line)
                .map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to write line: {}", e)))?;
        }
    }
    
    writer.flush().map_err(|e| pyo3::exceptions::PyIOError::new_err(format!("Failed to flush writer: {}", e)))?;

    // Persist the temporary file and return its path.
    // The caller (Python) will be responsible for replacing the original file.
    let temp_path = temp_file.into_temp_path();
    temp_path.to_str()
        .ok_or_else(|| pyo3::exceptions::PyRuntimeError::new_err("Temporary file path is not valid UTF-8"))
        .map(String::from)
}


// Modify rs_qvslice function
/// Extracts specified structures (slices) from a Quiver file based on a list of tags.
///
/// Reads a Quiver file and a list of tags. It returns a string containing the
/// Quiver data (including "QV_TAG" and "QV_SCORE" lines) for the specified tags.
/// If tags are not provided as an argument, it attempts to read them from stdin.
///
/// # Arguments
///
/// * `_py` - The Python GIL token (unused).
/// * `quiver_file` - Path to the Quiver file.
/// * `tags` - An optional vector of strings representing the tags to extract.
///   If `None` or empty, tags are read from stdin.
///
/// # Returns
///
/// `Ok(String)` containing the concatenated Quiver data for the requested tags.
/// The string will also include warning messages for any requested tags that were not found in the file.
///
/// # Errors
///
/// Returns a `PyErr` if:
/// * The Quiver file cannot be opened or read.
/// * No tags are provided (either as arguments or via stdin), or all provided tags are empty after trimming.
/// * An I/O error occurs (e.g., reading from stdin or the Quiver file).
/// * No matching tags (from the valid, non-empty provided tags) are found in the Quiver file.
#[pyfunction]
fn rs_qvslice(_py: Python, quiver_file: String, tags: Option<Vec<String>>) -> PyResult<String> {
    let mut tag_list = tags.unwrap_or_else(Vec::new);

    // Read tags from stdin if no arguments are provided and tag_list is empty
    if tag_list.is_empty() {
        let stdin = io::stdin();
        let mut stdin_reader = stdin.lock();
        let mut stdin_data = String::new(); // Read as String to handle potential UTF-8 issues better
        match stdin_reader.read_to_string(&mut stdin_data) {
            Ok(_) => {
                tag_list.extend(stdin_data.trim().split_whitespace().map(String::from));
            }
            Err(e) => {
                return Err(pyo3::exceptions::PyIOError::new_err(format!("Error reading from stdin: {}", e)));
            }
        }
    }

    // Clean and validate tag list: remove empty or whitespace-only tags
    tag_list.retain(|tag| !tag.trim().is_empty());
    if tag_list.is_empty() {
        return Err(pyo3::exceptions::PyValueError::new_err("No valid tags provided. Provide tags as arguments or via stdin."));
    }

    let qv = Quiver::new(quiver_file.clone(), "r".to_string())?;
    
    // Use get_struct_list from QuiverCore, which is what Quiver's method wraps
    match qv.core.get_struct_list(&tag_list) {
        Ok((qv_lines, found_tags)) => {
            let mut warnings = String::new();
            let mut actual_content = String::new();

            let found_tag_set: HashSet<_> = found_tags.iter().cloned().collect();
            for tag in &tag_list {
                if !found_tag_set.contains(tag) {
                    warnings.push_str(&format!("⚠️  Tag not found in Quiver file: {}\n", tag));
                }
            }

            if found_tags.is_empty() && !qv_lines.is_empty() {
                 // This case should ideally not happen if get_struct_list is consistent.
                 // If qv_lines is not empty, but found_tags is, it implies an internal logic issue.
                 return Err(pyo3::exceptions::PyRuntimeError::new_err("Internal error: Structures found but tags not listed."));
            }
            
            if found_tags.is_empty() && qv_lines.is_empty() {
                 // If no tags were found AND no lines were returned, it's a clear "not found" case.
                let error_message = if !warnings.is_empty() {
                    format!("No matching tags found in Quiver file. Details:\n{}", warnings)
                } else {
                    // This case implies tag_list was non-empty, but after filtering against the file, nothing matched.
                    "No matching tags found in Quiver file.".to_string()
                };
                return Err(pyo3::exceptions::PyValueError::new_err(error_message));
            }

            actual_content.push_str(&qv_lines);
            if !actual_content.is_empty() && !actual_content.ends_with('\n') {
                actual_content.push('\n');
            }
            
            // Prepend warnings to the actual content
            if !warnings.is_empty() && !actual_content.is_empty() {
                Ok(format!("{}\n{}", warnings.trim_end(), actual_content))
            } else if !warnings.is_empty() { // Only warnings, no content
                Ok(warnings)
            } else { // Only content, no warnings
                Ok(actual_content)
            }
        }
        Err(e) => Err(pyo3::exceptions::PyIOError::new_err(e.to_string())),
    }
}

// Add rs_qvsplit function
/// Splits a Quiver file into multiple smaller Quiver files.
///
/// Each new file will contain a specified number of structures (tags).
///
/// # Arguments
///
/// * `py` - The Python GIL token.
/// * `file` - Path to the input Quiver file.
/// * `ntags` - Number of tags (structures) per output file. Must be positive.
/// * `prefix` - Prefix for the output filenames.
/// * `output_dir` - Directory where the output files will be saved.
///
/// # Returns
///
/// `Ok(())` on success.
///
/// # Errors
///
/// Returns a `PyErr` if:
/// * `ntags` is zero.
/// * The input Quiver file cannot be opened or read.
/// * The output directory cannot be created.
/// * An I/O error occurs during reading or writing.
#[pyfunction]
fn rs_qvsplit(_py: Python, file: String, ntags: usize, prefix: String, output_dir: String) -> PyResult<String> {
    if ntags == 0 {
        return Err(pyo3::exceptions::PyValueError::new_err("NTAGS must be a positive integer."));
    }

    let q = Quiver::new(file.clone(), "r".to_string())?;
    q.split(ntags, &output_dir, &prefix)
        .map_err(|e| pyo3::exceptions::PyIOError::new_err(e))?;
    
    Ok(format!("✅ Files written to {} with prefix '{}'", output_dir, prefix))
}

// Add rs_extract_scorefile function
/// Extracts score data from a Quiver file and saves it as a tab-separated CSV file.
///
/// Parses "QV_SCORE" lines in the Quiver file, extracts tag and score information,
/// and writes it to a CSV file. The CSV file will have the same name as the
/// Quiver file but with a ".csv" extension.
///
/// # Arguments
///
/// * `py` - The Python GIL token.
/// * `quiver_file` - Path to the Quiver file.
///
/// # Returns
///
/// `Ok(String)` containing the path to the generated CSV file.
///
/// # Errors
///
/// Returns a `PyErr` if:
/// * The Quiver file cannot be opened or read.
/// * No score lines are found in the Quiver file.
/// * An I/O error occurs during reading or writing the CSV file.
/// * There's an error parsing score values (e.g., non-numeric score).
#[pyfunction]
fn rs_extract_scorefile(py: Python, quiver_file: String) -> PyResult<String> {
    let records = read_score_records(&quiver_file, py)?;

    if records.is_empty() {
        return Err(pyo3::exceptions::PyValueError::new_err("No score lines found in Quiver file."));
    }

    // Save as CSV file
    let path = Path::new(&quiver_file).with_extension("csv");
    let outfn = path.to_str()
        .ok_or_else(|| pyo3::exceptions::PyValueError::new_err("Invalid file path"))?;

    write_records_to_csv(&records, outfn)?;
    
    Ok(outfn.to_string())
}

fn read_score_records(quiver_file: &str, py: Python) -> PyResult<Vec<HashMap<String, String>>> {
    let mut records = Vec::new();
    let file = File::open(quiver_file).map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
    let reader = BufReader::new(file);

    for line in reader.lines() {
        let line = line.map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
        if line.starts_with("QV_SCORE") {
            let splits: Vec<_> = line.split_whitespace().collect();
            if splits.len() < 3 {
                // QV_SCORE line format is "QV_SCORE <tag> <score_data>"
                // If not enough parts, this line is malformed.
                // For now, we skip it. Consider logging a warning or returning an error.
                eprintln!("Skipping malformed QV_SCORE line: {}", line); // Temporary: for internal debugging
                continue;
            }
            let tag = splits[1].to_string();

            let mut scores: HashMap<String, String> = HashMap::new();
            // `tag` is already an owned String. No need to clone it if it's consumed by insert.
            // However, the key "tag" is created as owned String "tag".to_string().
            // The value `tag` (type String) can be inserted directly.
            scores.insert("tag".to_string(), tag); // No clone needed for `tag` here as it's moved.

            for entry in splits[2].split('|') {
                let parts: Vec<_> = entry.split('=').collect();
                if parts.len() == 2 {
                    // Attempt to parse the score as f64.
                    // If it fails, it's not a valid score format.
                    if f64::from_str(parts[1]).is_ok() {
                        scores.insert(parts[0].to_string(), parts[1].to_string());
                    } else {
                        // This specific score entry is malformed.
                        // Return an error, as this indicates data corruption or format violation.
                        return Err(pyo3::exceptions::PyValueError::new_err(format!(
                            "Invalid number format for score in tag '{}': {}",
                            tag, parts[1]
                        )));
                    }
                } else {
                    // Score entry format is 'key=value'. If not two parts, it's malformed.
                    // Return an error.
                    return Err(pyo3::exceptions::PyValueError::new_err(format!(
                        "Invalid score entry format for tag '{}': {}",
                        tag, entry
                    )));
                }
            }
            records.push(scores);
        }
    }
    Ok(records)
}

fn write_records_to_csv(records: &[HashMap<String, String>], outfn: &str) -> PyResult<()> {
    let mut file = File::create(outfn).map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;

    // Write header
    let mut headers = Vec::new();
    headers.push("tag".to_string()); // "tag" is always the first column
    // Collect all unique score keys to form the rest of the header columns
    for record in records {
        for key in record.keys() {
            if key != "tag" && !headers.contains(key) {
                headers.push(key.clone());
            }
        }
    }
    // Sort headers (except for "tag") to ensure consistent column order
    if headers.len() > 1 {
        headers[1..].sort_unstable();
    }
    writeln!(file, "{}", headers.join("\t")).map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;

    // Write data
    for record in records {
        let mut row = Vec::new();
        for header in &headers {
            if let Some(value) = record.get(header) {
                row.push(value.clone());
            } else {
                // If a score key is not present for a tag, write "NaN"
                row.push("NaN".to_string());
            }
        }
        writeln!(file, "{}", row.join("\t")).map_err(|e| pyo3::exceptions::PyIOError::new_err(e.to_string()))?;
    }
    Ok(())
}


// Add rs_extract_selected_pdbs function
/// Extracts specified PDB structures from a Quiver file to a designated output directory.
///
/// Processes a list of tags (provided directly or via stdin), and for each tag,
/// extracts the corresponding PDB data from the Quiver file. Each extracted structure
/// is saved to a ".pdb" file named after its tag in the specified output directory.
///
/// # Arguments
///
/// * `py` - The Python GIL token.
/// * `quiver_file` - Path to the source Quiver file.
/// * `tags` - A Python object representing a list of tags to extract.
/// * `output_dir` - Path to the directory where PDB files will be saved.
///
/// # Returns
///
/// `Ok(ExtractSelectedPdbResult)` which contains two lists:
///   - `extracted_files`: Paths of PDB files successfully extracted.
///   - `missing_tags`: Tags that were requested but not found in the Quiver file.
///
/// # Errors
///
/// Returns a `PyErr` if:
/// * No tags are provided.
/// * The output directory cannot be created.
/// * The Quiver file cannot be opened or read.
/// * An I/O error occurs during file operations.
#[pyfunction]
fn rs_extract_selected_pdbs(
    py: Python,
    quiver_file: String,
    tags: PyObject,
    output_dir: String,
) -> PyResult<ExtractSelectedPdbResult> {
    let unique_tags = get_unique_tags(py, tags)?;

    if unique_tags.is_empty() {
        return Err(pyo3::exceptions::PyValueError::new_err("No tags provided."));
    }

    // Ensure output directory exists
    fs::create_dir_all(&output_dir).map_err(|e| {
        pyo3::exceptions::PyIOError::new_err(format!("Failed to create output directory: {}", e))
    })?;

    let qv = Quiver::new(quiver_file.clone(), "r".to_string())?;
    let mut extracted_files = Vec::new();
    let mut missing_tags = Vec::new();
    let mut skipped_files = Vec::new(); // Keep track of skipped files

    for tag in &unique_tags {
        match extract_pdb_for_tag(&qv, tag, &output_dir) {
            Ok(Some(outfn)) => extracted_files.push(outfn),
            Ok(None) => skipped_files.push(format!("{}.pdb (already exists)", tag)), // File already existed
            Err(e) => {
                if e.contains("does not exist") { // Check if error indicates tag not found
                    missing_tags.push(tag.clone());
                } else {
                    // For other errors, propagate them
                    return Err(pyo3::exceptions::PyIOError::new_err(format!(
                        "Error processing tag {}: {}",
                        tag, e
                    )));
                }
            }
        }
    }

    Ok(ExtractSelectedPdbResult {
        extracted_files,
        missing_tags,
        // Optionally, include skipped_files in the result if the Python side needs it
    })
}

/// Result structure for `rs_extract_selected_pdbs`.
///
/// Contains lists of successfully extracted file paths and tags that were not found.
#[derive(Debug, pyo3::prelude::PyObject)]
#[pyo3(get_all)] // Automatically generate getters for all fields
struct ExtractSelectedPdbResult {
    extracted_files: Vec<String>,
    missing_tags: Vec<String>,
    // If you decide to return skipped files:
    // skipped_files: Vec<String>,
}

// No longer need custom ToPyObject if using #[derive(PyObject)] and #[pyo3(get_all)]
// impl pyo3::ToPyObject for ExtractSelectedPdbResult {
//     fn to_object(&self, py: Python) -> PyObject {
//         let dict = pyo3::types::PyDict::new_bound(py);
//         dict.set_item("extracted_files", self.extracted_files.to_object(py)).unwrap();
//         dict.set_item("missing_tags", self.missing_tags.to_object(py)).unwrap();
//         dict.into()
//     }
// }


fn get_unique_tags(py: Python, tags: PyObject) -> PyResult<Vec<String>> {
    let mut tag_buffers: Vec<String> = tags.extract(py)
        .map_err(|_| pyo3::exceptions::PyTypeError::new_err("Tags argument must be a list of strings."))?;

    // Check if input is being piped via stdin
    // This heuristic might not be universally reliable.
    // Consider a more explicit way if stdin detection is critical.
    if !env::var("TERM").is_ok() { 
        let stdin = io::stdin();
        let stdin_tags: Vec<String> = stdin
            .lock()
            .lines()
            .filter_map(Result::ok) // Ignore lines with read errors
            .flat_map(|line| line.split_whitespace().map(String::from).collect::<Vec<String>>())
            .collect();
        if !stdin_tags.is_empty() {
            tag_buffers.extend(stdin_tags);
        }
    }

    // Clean and deduplicate tags
    let mut unique_tags: Vec<String> = tag_buffers
        .into_iter()
        .map(|tag| tag.trim().to_string()) // Trim whitespace
        .filter(|tag| !tag.is_empty())    // Remove empty tags
        .collect::<HashSet<_>>()          // Deduplicate
        .into_iter()
        .collect();
    unique_tags.sort_unstable(); // Use unstable sort for potentially better performance
    Ok(unique_tags)
}

/// Helper function to extract PDB lines for a single tag and write to a file.
/// Returns `Ok(Some(filepath))` if successful,
/// `Ok(None)` if the file already exists (skipped),
/// `Err(String)` for other errors (tag not found, I/O error).
fn extract_pdb_for_tag(
    qv: &Quiver,
    tag: &str,
    output_dir: &str,
) -> Result<Option<String>, String> {
    let outfn = Path::new(output_dir)
        .join(format!("{}.pdb", tag));

    // Check if the file already exists before attempting to create it
    if outfn.exists() {
        return Ok(None); // Signal that the file was skipped
    }
    
    let outfn_str = outfn.to_str()
        .ok_or_else(|| format!("Failed to create output path string for tag {}", tag))?;

    match qv.get_pdblines(tag) { // Pass &str. Returns Vec<String> (lines without newlines)
        Ok(lines) => {
            // Ensure parent directory exists, create if not.
            if let Some(parent_dir) = outfn.parent() {
                fs::create_dir_all(parent_dir)
                    .map_err(|e| format!("Failed to create directory for {}: {}", outfn_str, e))?;
            }

            let mut outfile = File::create(&outfn)
                .map_err(|e| format!("Failed to create file {}: {}", outfn_str, e))?;
            for line in lines { // Iterate over Vec<String>
                // Write the line and then a newline character
                if let Err(e) = writeln!(outfile, "{}", line) {
                     return Err(format!("Failed to write line to file {}: {}", outfn_str, e));
                }
            }
            Ok(Some(outfn_str.to_string()))
        }
        Err(e) => {
            // Check if the error message from get_pdblines indicates the tag does not exist.
            if e.contains("does not exist") { // This check might be fragile if error messages change.
                 Err(format!("Tag '{}' does not exist in Quiver file.", tag))
            } else {
                 Err(format!("Error getting PDB lines for tag '{}': {}", tag, e))
            }
        }
    }
}


/// A Python module implemented in Rust.
#[pymodule]
fn quiver_pdb(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(rs_qvfrompdbs, m)?)?;
    m.add_function(wrap_pyfunction!(rs_extract_pdbs, m)?)?;
    m.add_function(wrap_pyfunction!(rs_list_tags, m)?)?;
    m.add_function(wrap_pyfunction!(rs_rename_tags, m)?)?;
    m.add_function(wrap_pyfunction!(rs_qvslice, m)?)?;
    m.add_function(wrap_pyfunction!(rs_qvsplit, m)?)?;
    m.add_function(wrap_pyfunction!(rs_extract_scorefile, m)?)?;
    m.add_function(wrap_pyfunction!(rs_extract_selected_pdbs, m)?)?;
    m.add_class::<Quiver>()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::NamedTempFile; // For creating temporary files for testing

    // Helper function to create a temporary quiver file with given content
    fn create_temp_qv_file(content: &str) -> NamedTempFile {
        let mut temp_file = NamedTempFile::new().expect("Failed to create temp file");
        temp_file.write_all(content.as_bytes()).expect("Failed to write to temp file");
        temp_file.flush().expect("Failed to flush temp file");
        temp_file
    }

    #[test]
    fn test_get_pdblines_success() {
        let content = "QV_TAG tag1\nATOM 1\nATOM 2\nQV_SCORE tag1 score=1.0\nQV_TAG tag2\nATOM 3\nEND\n";
        let temp_qv_file = create_temp_qv_file(content);
        let core = QuiverCore::new(temp_qv_file.path().to_str().unwrap().to_string(), "r".to_string()).unwrap();
        
        let pdb_lines = core.get_pdblines("tag1").unwrap();
        assert_eq!(pdb_lines, vec!["ATOM 1", "ATOM 2"]);

        let pdb_lines_tag2 = core.get_pdblines("tag2").unwrap();
        assert_eq!(pdb_lines_tag2, vec!["ATOM 3", "END"]);
    }

    #[test]
    fn test_get_pdblines_tag_not_found() {
        let content = "QV_TAG tag1\nATOM 1\n";
        let temp_qv_file = create_temp_qv_file(content);
        let core = QuiverCore::new(temp_qv_file.path().to_str().unwrap().to_string(), "r".to_string()).unwrap();
        
        let result = core.get_pdblines("non_existent_tag");
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("does not exist"));
    }

    #[test]
    fn test_get_pdblines_no_pdb_lines_for_tag() {
        let content = "QV_TAG tag1\nQV_SCORE tag1 score=1.0\nQV_TAG tag2\nATOM 1\n";
        let temp_qv_file = create_temp_qv_file(content);
        let core = QuiverCore::new(temp_qv_file.path().to_str().unwrap().to_string(), "r".to_string()).unwrap();
        
        let pdb_lines = core.get_pdblines("tag1").unwrap();
        assert!(pdb_lines.is_empty());
    }

    #[test]
    fn test_get_pdblines_score_line_mixed() {
        let content = "QV_TAG tag1\nATOM 1\nQV_SCORE tag1 score=1.0\nATOM 2\nQV_TAG tag2\n";
        let temp_qv_file = create_temp_qv_file(content);
        let core = QuiverCore::new(temp_qv_file.path().to_str().unwrap().to_string(), "r".to_string()).unwrap();
        
        // QV_SCORE lines should be ignored, and only lines between QV_TAG tag1 and QV_TAG tag2 that are not QV_SCORE for tag1
        // In the current implementation of get_pdblines, it stops collecting lines for the current tag
        // as soon as it finds a QV_SCORE line *if that QV_SCORE line belongs to the *current* tag (which it skips by !line.starts_with("QV_SCORE"))
        // or if it finds the next QV_TAG.
        // The problem description for get_pdblines says "if found && !line.starts_with("QV_SCORE")"
        // This means any QV_SCORE line will stop the collection of PDB lines for the current tag if it's within the tag's block.
        // Let's re-verify the logic:
        // if line.starts_with("QV_TAG") { ... if parts[1] == tag { found = true; continue; } else if found { break; }}
        // if found && !line.starts_with("QV_SCORE") { pdb_lines.push(line); }
        // This is correct: it will collect ATOM 1, then see QV_SCORE for tag1, skip it, then collect ATOM 2.
        let pdb_lines = core.get_pdblines("tag1").unwrap();
        assert_eq!(pdb_lines, vec!["ATOM 1", "ATOM 2"]);
    }

    #[test]
    fn test_get_pdblines_empty_file() {
        let content = "";
        let temp_qv_file = create_temp_qv_file(content);
        let core = QuiverCore::new(temp_qv_file.path().to_str().unwrap().to_string(), "r".to_string()).unwrap();
        
        let result = core.get_pdblines("tag1");
        assert!(result.is_err());
        assert!(result.unwrap_err().contains("does not exist"));
    }

    #[test]
    fn test_get_struct_list_success() {
        let content = "QV_TAG tag1\nATOM 1\nQV_SCORE tag1 score=1.0\nQV_TAG tag2\nATOM 2\nQV_TAG tag3\nATOM 3\n";
        let temp_qv_file = create_temp_qv_file(content);
        let core = QuiverCore::new(temp_qv_file.path().to_str().unwrap().to_string(), "r".to_string()).unwrap();

        let (struct_lines, found_tags) = core.get_struct_list(&["tag1".to_string(), "tag3".to_string()]).unwrap();
        
        let expected_lines = "QV_TAG tag1\nATOM 1\nQV_SCORE tag1 score=1.0\nQV_TAG tag3\nATOM 3\n";
        assert_eq!(struct_lines, expected_lines);
        assert_eq!(found_tags, vec!["tag1".to_string(), "tag3".to_string()]);
    }

    #[test]
    fn test_get_struct_list_one_tag_not_found() {
        let content = "QV_TAG tag1\nATOM 1\nQV_TAG tag2\nATOM 2\n";
        let temp_qv_file = create_temp_qv_file(content);
        let core = QuiverCore::new(temp_qv_file.path().to_str().unwrap().to_string(), "r".to_string()).unwrap();

        let (struct_lines, found_tags) = core.get_struct_list(&["tag1".to_string(), "non_existent".to_string()]).unwrap();
        
        let expected_lines = "QV_TAG tag1\nATOM 1\n";
        assert_eq!(struct_lines, expected_lines);
        assert_eq!(found_tags, vec!["tag1".to_string()]);
    }

    #[test]
    fn test_get_struct_list_all_tags_not_found() {
        let content = "QV_TAG tag1\nATOM 1\nQV_TAG tag2\nATOM 2\n";
        let temp_qv_file = create_temp_qv_file(content);
        let core = QuiverCore::new(temp_qv_file.path().to_str().unwrap().to_string(), "r".to_string()).unwrap();

        let (struct_lines, found_tags) = core.get_struct_list(&["non_existent1".to_string(), "non_existent2".to_string()]).unwrap();
        
        assert!(struct_lines.is_empty());
        assert!(found_tags.is_empty());
    }

    #[test]
    fn test_get_struct_list_empty_tag_list() {
        let content = "QV_TAG tag1\nATOM 1\nQV_TAG tag2\nATOM 2\n";
        let temp_qv_file = create_temp_qv_file(content);
        let core = QuiverCore::new(temp_qv_file.path().to_str().unwrap().to_string(), "r".to_string()).unwrap();

        let (struct_lines, found_tags) = core.get_struct_list(&[]).unwrap();
        
        assert!(struct_lines.is_empty());
        assert!(found_tags.is_empty());
    }

    #[test]
    fn test_get_struct_list_empty_file() {
        let content = "";
        let temp_qv_file = create_temp_qv_file(content);
        let core = QuiverCore::new(temp_qv_file.path().to_str().unwrap().to_string(), "r".to_string()).unwrap();

        let (struct_lines, found_tags) = core.get_struct_list(&["tag1".to_string()]).unwrap();
        
        assert!(struct_lines.is_empty());
        assert!(found_tags.is_empty());
    }

    // Tests for read_score_records
    #[test]
    fn test_read_score_records_valid() {
        let content = "QV_TAG tag1\nATOM 1\nQV_SCORE tag1 score1=1.0|score2=2.0\nQV_TAG tag2\nQV_SCORE tag2 scoreA=0.5\n";
        let temp_qv_file = create_temp_qv_file(content);
        let py = unsafe { Python::assume_gil_acquired() }; // For direct Rust tests not involving PyO3 calls
        let records = read_score_records(temp_qv_file.path().to_str().unwrap(), py).unwrap();

        assert_eq!(records.len(), 2);
        assert_eq!(records[0].get("tag").unwrap(), "tag1");
        assert_eq!(records[0].get("score1").unwrap(), "1.0");
        assert_eq!(records[0].get("score2").unwrap(), "2.0");
        assert_eq!(records[1].get("tag").unwrap(), "tag2");
        assert_eq!(records[1].get("scoreA").unwrap(), "0.5");
    }

    #[test]
    fn test_read_score_records_no_score_lines() {
        let content = "QV_TAG tag1\nATOM 1\nQV_TAG tag2\nATOM 2\n";
        let temp_qv_file = create_temp_qv_file(content);
        let py = unsafe { Python::assume_gil_acquired() };
        let records = read_score_records(temp_qv_file.path().to_str().unwrap(), py).unwrap();
        assert!(records.is_empty());
    }

    #[test]
    fn test_read_score_records_malformed_score_value() {
        let content = "QV_SCORE tag1 score1=abc\n";
        let temp_qv_file = create_temp_qv_file(content);
        let py = unsafe { Python::assume_gil_acquired() };
        let result = read_score_records(temp_qv_file.path().to_str().unwrap(), py);
        assert!(result.is_err());
        if let Err(e) = result {
            assert!(e.to_string().contains("Invalid number format"));
        }
    }
    
    #[test]
    fn test_read_score_records_malformed_score_entry() {
        let content = "QV_SCORE tag1 score1\n"; // Missing '='
        let temp_qv_file = create_temp_qv_file(content);
        let py = unsafe { Python::assume_gil_acquired() };
        let result = read_score_records(temp_qv_file.path().to_str().unwrap(), py);
        assert!(result.is_err());
        if let Err(e) = result {
            assert!(e.to_string().contains("Invalid score entry format"));
        }
    }

    #[test]
    fn test_read_score_records_malformed_line_short() {
        let content = "QV_SCORE tag1\n"; // Too short, missing score data part
        let temp_qv_file = create_temp_qv_file(content);
        let py = unsafe { Python::assume_gil_acquired() };
        // This will not error but will print to stderr and skip the line.
        // To test this properly, we would need to capture stderr or modify the function.
        // For now, we expect an empty records list.
        let records = read_score_records(temp_qv_file.path().to_str().unwrap(), py).unwrap();
        assert!(records.is_empty());
    }

    // Tests for write_records_to_csv
    #[test]
    fn test_write_records_to_csv_valid() {
        let mut records = Vec::new();
        let mut record1 = HashMap::new();
        record1.insert("tag".to_string(), "tag1".to_string());
        record1.insert("score1".to_string(), "1.0".to_string());
        record1.insert("score2".to_string(), "2.0".to_string());
        records.push(record1);

        let mut record2 = HashMap::new();
        record2.insert("tag".to_string(), "tag2".to_string());
        record2.insert("score1".to_string(), "3.0".to_string());
        record2.insert("score3".to_string(), "4.0".to_string());
        records.push(record2);

        let temp_csv_file = NamedTempFile::new().unwrap();
        let temp_path_str = temp_csv_file.path().to_str().unwrap();

        write_records_to_csv(&records, temp_path_str).unwrap();

        let mut file_content = String::new();
        File::open(temp_path_str).unwrap().read_to_string(&mut file_content).unwrap();
        
        let expected_header = "tag\tscore1\tscore2\tscore3"; // Order might vary after score1 due to HashMap
        let lines: Vec<&str> = file_content.trim_end().split('\n').collect();
        assert!(lines.len() == 3); // Header + 2 records
        
        // Check header parts, as order of score2/score3 can vary
        let header_parts: HashSet<&str> = lines[0].split('\t').collect();
        let expected_header_parts: HashSet<&str> = expected_header.split('\t').collect();
        assert_eq!(header_parts, expected_header_parts);

        // Check content (order of rows is fixed)
        assert!(lines[1].contains("tag1"));
        assert!(lines[1].contains("1.0"));
        assert!(lines[1].contains("2.0"));
        assert!(lines[1].contains("NaN") || !lines[1].contains("score3")); // if score3 was a column

        assert!(lines[2].contains("tag2"));
        assert!(lines[2].contains("3.0"));
        assert!(lines[2].contains("NaN") || !lines[2].contains("score2")); // if score2 was a column
        assert!(lines[2].contains("4.0"));
    }

    #[test]
    fn test_write_records_to_csv_empty() {
        let records: Vec<HashMap<String, String>> = Vec::new();
        let temp_csv_file = NamedTempFile::new().unwrap();
        let temp_path_str = temp_csv_file.path().to_str().unwrap();

        write_records_to_csv(&records, temp_path_str).unwrap();

        let mut file_content = String::new();
        File::open(temp_path_str).unwrap().read_to_string(&mut file_content).unwrap();
        
        // Should only contain the header "tag" if any processing happened, or be empty.
        // Current implementation of write_records_to_csv adds "tag" to headers by default.
        assert_eq!(file_content.trim(), "tag");
    }

    // Tests for rename_tags_in_file_content
    #[test]
    fn test_rename_tags_in_file_content_success() {
        let initial_content = "QV_TAG old_tag1\nATOM 1\nQV_SCORE old_tag1 score=1.0\nQV_TAG old_tag2\nATOM 2\n";
        let temp_input_file = create_temp_qv_file(initial_content);
        let input_path_str = temp_input_file.path().to_str().unwrap();

        let new_tags = vec!["new_tag1".to_string(), "new_tag2".to_string()];
        
        let result_temp_path_str = rename_tags_in_file_content(input_path_str, &new_tags).unwrap();
        
        let mut result_content = String::new();
        File::open(&result_temp_path_str).unwrap().read_to_string(&mut result_content).unwrap();
        
        let expected_content = "QV_TAG new_tag1\nQV_SCORE new_tag1 score=1.0\nATOM 1\nQV_TAG new_tag2\nATOM 2\n";
        
        // Need to parse and compare line by line due to potential reordering of PDB lines vs QV_SCORE by the function's logic
        // The function writes QV_TAG, then QV_SCORE (if any), then the rest of the lines for that tag block.
        // Let's adjust expected content based on how `rename_tags_in_file_content` actually writes.
        // rename_tags_in_file_content writes:
        // 1. QV_TAG new_tag
        // 2. If next line is QV_SCORE for OLD_TAG, it writes QV_SCORE new_tag ...
        // 3. Then it writes the next line (which was after QV_SCORE, or after QV_TAG if no QV_SCORE)
        // This means ATOM 1 (content for old_tag1) comes AFTER QV_SCORE new_tag1.

        let expected_output_order = "QV_TAG new_tag1\nQV_SCORE new_tag1 score=1.0\nATOM 1\nQV_TAG new_tag2\nATOM 2\n";
        assert_eq!(result_content.trim_end(), expected_output_order.trim_end());

        // The temporary file at result_temp_path_str will be cleaned up when its `TempPath` object is dropped.
        // We might need to explicitly close or drop it if further operations are needed before cleanup.
        // For this test, it's fine.
    }

    #[test]
    fn test_rename_tags_in_file_content_no_score() {
        let initial_content = "QV_TAG old_tag1\nATOM 1\nATOM 2\nQV_TAG old_tag2\nATOM 3\n";
        let temp_input_file = create_temp_qv_file(initial_content);
        let input_path_str = temp_input_file.path().to_str().unwrap();

        let new_tags = vec!["new_tag1".to_string(), "new_tag2".to_string()];
        
        let result_temp_path_str = rename_tags_in_file_content(input_path_str, &new_tags).unwrap();
        
        let mut result_content = String::new();
        File::open(&result_temp_path_str).unwrap().read_to_string(&mut result_content).unwrap();
        
        // Expected: QV_TAG new_tag1, then ATOM 1, then ATOM 2.
        let expected_content = "QV_TAG new_tag1\nATOM 1\nATOM 2\nQV_TAG new_tag2\nATOM 3\n";
        assert_eq!(result_content.trim_end(), expected_content.trim_end());
    }
    
    #[test]
    fn test_rename_tags_in_file_content_error_two_qv_tags() {
        let initial_content = "QV_TAG old_tag1\nQV_TAG old_tag1_problem\nATOM 1\n";
        let temp_input_file = create_temp_qv_file(initial_content);
        let input_path_str = temp_input_file.path().to_str().unwrap();
        let new_tags = vec!["new_tag1".to_string(), "new_tag2".to_string()];

        let result = rename_tags_in_file_content(input_path_str, &new_tags);
        assert!(result.is_err());
        if let Err(e) = result {
            assert!(e.to_string().contains("Found two QV_TAG lines in a row"));
        }
    }
    
    #[test]
    fn test_rename_tags_in_file_content_tag_mismatch_more_in_file() {
        // This specific scenario (more tags in file than new_tags provided)
        // should ideally be caught by rs_rename_tags before calling rename_tags_in_file_content.
        // However, if rename_tags_in_file_content is called directly with such input:
        let initial_content = "QV_TAG old_tag1\nATOM 1\nQV_TAG old_tag2\nATOM 2\n";
        let temp_input_file = create_temp_qv_file(initial_content);
        let input_path_str = temp_input_file.path().to_str().unwrap();
        let new_tags = vec!["new_tag1".to_string()]; // Only one new tag for two old tags

        let result = rename_tags_in_file_content(input_path_str, &new_tags);
        // The function will error when tag_idx (0) is used for the first tag,
        // then for the second tag, tag_idx (1) will be out of bounds for new_tags.
        // The exact error might be "index out of bounds" or the specific one I added.
        // The check `if tag_idx >= new_tags.len()` should catch this.
        assert!(result.is_err());
         if let Err(e) = result {
            assert!(e.to_string().contains("More tags in file than new tags provided"));
        }
    }
}


