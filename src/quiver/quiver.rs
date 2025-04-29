use std::collections::HashSet;
use std::fs::{self, File, OpenOptions};
use std::io::{self, BufRead, BufReader, BufWriter, Write};
use std::path::{Path, PathBuf};

#[derive(Debug)]
pub enum QuiverError {
    Io(io::Error),
    InvalidMode(String),
    DuplicateTag(String),
    TagNotFound(String),
    InvalidOperation(String),
}

impl From<io::Error> for QuiverError {
    fn from(err: io::Error) -> Self {
        QuiverError::Io(err)
    }
}

pub struct Quiver {
    filename: PathBuf,
    mode: String,
    tags: Vec<String>,
}

impl Quiver {
    pub fn new<P: AsRef<Path>>(filename: P, mode: &str) -> Result<Self, QuiverError> {
        if mode != "r" && mode != "w" {
            return Err(QuiverError::InvalidMode(format!(
                "Quiver file must be opened in 'r' or 'w' mode, not '{}'",
                mode
            )));
        }
        let filename = filename.as_ref().to_path_buf();
        let tags = Self::read_tags(&filename)?;
        Ok(Self {
            filename,
            mode: mode.to_string(),
            tags,
        })
    }

    fn read_tags(filename: &Path) -> Result<Vec<String>, QuiverError> {
        if !filename.exists() {
            return Ok(vec![]);
        }
        let file = File::open(filename)?;
        let reader = BufReader::new(file);
        let tags = reader
            .lines()
            .filter_map(|line| {
                line.ok().and_then(|l| {
                    if l.starts_with("QV_TAG") {
                        l.split_whitespace().nth(1).map(|s| s.to_string())
                    } else {
                        None
                    }
                })
            })
            .collect();
        Ok(tags)
    }

    pub fn get_tags(&self) -> Vec<String> {
        self.tags.clone()
    }

    pub fn size(&self) -> usize {
        self.tags.len()
    }

    pub fn add_pdb(
        &mut self,
        pdb_lines: &[String],
        tag: &str,
        score_str: Option<&str>,
    ) -> Result<(), QuiverError> {
        if self.mode != "w" {
            return Err(QuiverError::InvalidOperation(
                "Quiver file must be opened in write mode to allow for writing.".to_string(),
            ));
        }
        if self.tags.contains(&tag.to_string()) {
            return Err(QuiverError::DuplicateTag(tag.to_string()));
        }

        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.filename)?;

        writeln!(file, "QV_TAG {}", tag)?;
        if let Some(score) = score_str {
            writeln!(file, "QV_SCORE {} {}", tag, score)?;
        }
        for line in pdb_lines {
            file.write_all(line.as_bytes())?;
            if !line.ends_with('\n') {
                file.write_all(b"\n")?;
            }
        }
        self.tags.push(tag.to_string());
        Ok(())
    }

    pub fn get_pdblines(&self, tag: &str) -> Result<Vec<String>, QuiverError> {
        if self.mode != "r" {
            return Err(QuiverError::InvalidOperation(
                "Quiver file must be opened in read mode to allow for reading.".to_string(),
            ));
        }
        let file = File::open(&self.filename)?;
        let reader = BufReader::new(file);
        let mut found = false;
        let mut pdb_lines = Vec::new();

        for line in reader.lines() {
            let line = line?;
            if line.starts_with("QV_TAG") {
                let current_tag = line.split_whitespace().nth(1).unwrap_or("");
                if current_tag == tag {
                    found = true;
                    continue;
                } else if found {
                    break;
                }
            }
            if found && !line.starts_with("QV_SCORE") {
                pdb_lines.push(line);
            }
        }
        if !found {
            return Err(QuiverError::TagNotFound(tag.to_string()));
        }
        Ok(pdb_lines)
    }

    pub fn get_struct_list(
        &self,
        tag_list: &[String],
    ) -> Result<(String, Vec<String>), QuiverError> {
        if self.mode != "r" {
            return Err(QuiverError::InvalidOperation(
                "Quiver file must be opened in read mode to allow for reading.".to_string(),
            ));
        }
        let tag_set: HashSet<_> = tag_list.iter().cloned().collect();
        let mut found_tags = Vec::new();
        let mut struct_lines = String::new();
        let mut write_mode = false;

        let file = File::open(&self.filename)?;
        let reader = BufReader::new(file);

        for line in reader.lines() {
            let line = line?;
            if line.starts_with("QV_TAG") {
                let current_tag = line.split_whitespace().nth(1).unwrap_or("").to_string();
                write_mode = tag_set.contains(&current_tag);
                if write_mode {
                    found_tags.push(current_tag);
                }
            }
            if write_mode {
                struct_lines.push_str(&line);
                struct_lines.push('\n');
            }
        }
        Ok((struct_lines, found_tags))
    }

    pub fn split(
        &self,
        ntags: usize,
        outdir: &str,
        prefix: &str,
    ) -> Result<(), QuiverError> {
        if self.mode != "r" {
            return Err(QuiverError::InvalidOperation(
                "Quiver file must be opened in read mode to allow for reading.".to_string(),
            ));
        }
        fs::create_dir_all(outdir)?;
        let mut file_idx = 0usize;
        let mut tag_count = 0usize;
        let mut out_file: Option<BufWriter<File>> = None;

        let file = File::open(&self.filename)?;
        let reader = BufReader::new(file);

        for line in reader.lines() {
            let line = line?;
            if line.starts_with("QV_TAG") {
                if tag_count % ntags == 0 {
                    if let Some(mut f) = out_file.take() {
                        f.flush()?;
                    }
                    let out_path = Path::new(outdir).join(format!("{}_{}.qv", prefix, file_idx));
                    out_file = Some(BufWriter::new(File::create(out_path)?));
                    file_idx += 1;
                }
                tag_count += 1;
            }
            if let Some(f) = out_file.as_mut() {
                writeln!(f, "{}", line)?;
            }
        }
        if let Some(mut f) = out_file {
            f.flush()?;
        }
        Ok(())
    }
}
