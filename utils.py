def format_full_profile(profile):
    return {
                "id": profile.id,
                "name": profile.name,
                "gender": profile.gender,
                "gender_probability": profile.gender_probability,
                "sample_size": profile.sample_size,
                "age": profile.age,
                "age_group": profile.age_group,
                "country_id": profile.country_id,
                "country_name": profile.country_name,
                "country_probability": profile.country_probability,
                "created_at": profile.created_at.strftime("%Y-%m-%dT%H:%M:%SZ")
            }